import time
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from database.session import get_db
from database.models import ChatSession, ChatMessage, Citation, AnalyticsLog, Document
from database.schemas import ChatQueryResponse, ChatSessionListResponse, ChatSessionResponse
from database.crud_helpers import get_or_create_user
from pipeline.generation import (
    run_guardrails,
    run_query_rewrite,
    generate_llm_text,
    build_citations
)
from pipeline.retrieval import retriever_instance, compress_context
from pipeline.faithfulness import check_faithfulness
from auth.clerk_auth import get_current_user_from_token

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG Pipeline"])

class ChatQueryRequest(BaseModel):
    session_id: Optional[int] = None
    query: str

@router.post("/query", response_model=ChatQueryResponse)
async def process_chat_query(
    req: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Complete Hybrid RAG Pipeline:
    User Question -> Guardrails -> Query Rewrite -> Hybrid Retrieval (FAISS+BM25) -> Cross Encoder Reranking -> Context Compression -> LLM -> Faithfulness Check -> Structured Citations
    """
    start_time = time.time()
    user_query = req.query.strip()

    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. Ensure or create Chat Session (scoped to the authenticated user)
    db_user = get_or_create_user(db, current_user)
    session = None
    if req.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == req.session_id,
            ChatSession.user_id == db_user.id
        ).first()

    if not session:
        session = ChatSession(
            user_id=db_user.id,
            title=user_query[:40] + ("..." if len(user_query) > 40 else "")
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save User Message to DB
    user_msg = ChatMessage(session_id=session.id, role="user", content=user_query)
    db.add(user_msg)
    db.commit()

    # 2. Guardrails Check
    is_safe, guardrail_msg = await run_guardrails(user_query)
    if not is_safe:
        bot_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=guardrail_msg,
            faithfulness_status="BLOCKED"
        )
        db.add(bot_msg)
        db.commit()

        # Log analytics
        log = AnalyticsLog(query=user_query, answered=False, response_time_ms=(time.time() - start_time) * 1000)
        db.add(log)
        db.commit()

        return {
            "session_id": session.id,
            "answer": guardrail_msg,
            "faithfulness_status": "BLOCKED",
            "citations": [],
            "retrieved_chunks_count": 0
        }

    # 3. Query Rewrite
    rewritten_query = await run_query_rewrite(user_query)

    # 4. Hybrid Retrieval & Re-ranking (FAISS + BM25 -> Top 30 -> Top 5 Reranked)
    retrieved_chunks = retriever_instance.hybrid_search(rewritten_query, top_k_dense=20, top_k_sparse=20, top_n_rerank=5)

    if not retrieved_chunks:
        answer_text = "No relevant documents have been uploaded or matched your query. Please upload document files first."
        bot_msg = ChatMessage(session_id=session.id, role="assistant", content=answer_text, faithfulness_status="INSUFFICIENT_EVIDENCE")
        db.add(bot_msg)
        db.commit()

        log = AnalyticsLog(query=user_query, answered=False, response_time_ms=(time.time() - start_time) * 1000)
        db.add(log)
        db.commit()

        return {
            "session_id": session.id,
            "answer": answer_text,
            "faithfulness_status": "INSUFFICIENT_EVIDENCE",
            "citations": [],
            "retrieved_chunks_count": 0
        }

    # 5. Context Compression
    compressed_context = compress_context(user_query, retrieved_chunks)

    # 6. LLM Generation (NVIDIA NIM -> Groq -> Local Fallback)
    system_prompt = (
        "You are an enterprise AI document assistant. Answer the user prompt accurately based ONLY on the provided CONTEXT. "
        "Include reference details if relevant."
    )
    llm_prompt = f"CONTEXT:\n{compressed_context}\n\nUSER QUESTION: {user_query}"
    raw_answer = await generate_llm_text(llm_prompt, system_prompt=system_prompt)

    # 7. Faithfulness Check
    is_faithful, final_answer = await check_faithfulness(
        raw_answer,
        retrieved_chunks,
        lambda p, system_prompt: generate_llm_text(p, system_prompt=system_prompt)
    )

    faithfulness_status = "FAITHFUL" if is_faithful else "INSUFFICIENT_EVIDENCE"

    # 8. Build Citations
    citations_data = build_citations(retrieved_chunks)

    # Save Assistant Message to DB
    bot_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=final_answer,
        faithfulness_status=faithfulness_status
    )
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)

    # Store Citations in DB
    citation_objs = []
    for c in citations_data:
        doc = db.query(Document).filter(Document.filename == c["filename"]).first()
        bbox = c.get("bbox") or {}
        cit = Citation(
            message_id=bot_msg.id,
            document_id=doc.id if doc else None,
            filename=c["filename"],
            page_number=c["page_number"],
            heading=c["heading"],
            section=c["section"],
            text_snippet=c["text_snippet"],
            bbox_x0=bbox.get("x0"),
            bbox_y0=bbox.get("y0"),
            bbox_x1=bbox.get("x1"),
            bbox_y1=bbox.get("y1")
        )
        db.add(cit)
        citation_objs.append(cit)

        # Increment document search count metric
        if doc:
            doc.search_count += 1

    db.commit()

    # Log Analytics
    elapsed_ms = (time.time() - start_time) * 1000
    analytics_entry = AnalyticsLog(
        query=user_query,
        document_filename=citations_data[0]["filename"] if citations_data else None,
        answered=is_faithful,
        response_time_ms=elapsed_ms
    )
    db.add(analytics_entry)
    db.commit()

    return {
        "session_id": session.id,
        "message_id": bot_msg.id,
        "answer": final_answer,
        "faithfulness_status": faithfulness_status,
        "citations": citations_data,
        "retrieved_chunks_count": len(retrieved_chunks),
        "response_time_ms": round(elapsed_ms, 2)
    }

@router.get("/sessions", response_model=List[ChatSessionListResponse])
def get_chat_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Returns history of chat sessions for the authenticated user.
    """
    db_user = get_or_create_user(db, current_user)
    rows = (
        db.query(ChatSession, func.count(ChatMessage.id))
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == db_user.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [{
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at,
        "message_count": count
    } for s, count in rows]

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Returns all messages and citations for a given chat session (owner only).
    """
    db_user = get_or_create_user(db, current_user)
    session = db.query(ChatSession).options(
        selectinload(ChatSession.messages).selectinload(ChatMessage.citations)
    ).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == db_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = []
    for msg in session.messages:
        citations = [{
            "citation_id": f"cit_{c.id}",
            "filename": c.filename,
            "page_number": c.page_number,
            "heading": c.heading,
            "section": c.section,
            "text_snippet": c.text_snippet,
            "bbox": {"x0": c.bbox_x0, "y0": c.bbox_y0, "x1": c.bbox_x1, "y1": c.bbox_y1} if c.bbox_x0 is not None else None
        } for c in msg.citations]

        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "faithfulness_status": msg.faithfulness_status,
            "timestamp": msg.timestamp,
            "citations": citations
        })

    return {
        "session_id": session.id,
        "title": session.title,
        "messages": messages
    }
