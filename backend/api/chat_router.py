import time
import asyncio
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
    t_rewrite = time.time()

    # 4. Hybrid Retrieval & Re-ranking (FAISS + BM25 -> Top 30 -> Top 5 Reranked)
    retrieved_chunks = await asyncio.to_thread(
        retriever_instance.hybrid_search,
        rewritten_query,
        top_k_dense=10,
        top_k_sparse=10,
        top_n_rerank=5
    )
    t_retrieval = time.time()
    print(f"[Chat] Retrieval took {t_retrieval - t_rewrite:.2f}s, found {len(retrieved_chunks)} chunks", flush=True)

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

    # 6. LLM Generation (Groq -> NVIDIA NIM -> Local Fallback)
    system_prompt = (
        "You are an Enterprise Anti-Hallucination Document AI. Rules:\n"
        "1. Answer ONLY from CONTEXT — strictly NO outside knowledge, speculation, or fabrication.\n"
        "2. Never invent dates, numbers, figures, or names not present in the CONTEXT.\n"
        "3. No explanations, labels, greetings, or citation markers.\n"
        "4. If the user asks to 'list' or 'all' (e.g. list all projects, list skills), "
        "output EVERY matching item separated by commas. Do NOT pick just one.\n"
        "5. For skills questions, output the SKILLS as a comma-separated list. "
        "Do NOT output the profile summary or objective paragraph.\n"
        "6. Typos in the question are normal — interpret what the user likely means.\n"
        "7. For specific fields like graduation year, roll number, guide name — "
        "extract ONLY that exact field, not a similar-looking number from elsewhere.\n"
        "8. If the CONTEXT truly has no answer, say exactly: Not found in the document.\n"
        "Examples (these show FORMAT ONLY — extract YOUR values strictly from CONTEXT):\n"
        "  What is the candidate's name? → [Name from context]\n"
        "  List all projects → [Project 1, Project 2]\n"
        "  What are the skills → [Skill 1, Skill 2, Skill 3]\n"
        "  Graduation year → [Year]\n"
    )
    llm_prompt = f"CONTEXT:\n{compressed_context}\n\nUSER QUESTION: {user_query}"
    t_gen_start = time.time()
    raw_answer = await generate_llm_text(llm_prompt, system_prompt=system_prompt)
    t_gen_end = time.time()
    print(f"[Chat] LLM generation took {t_gen_end - t_gen_start:.2f}s", flush=True)

    # 7. Faithfulness Check
    t_faith_start = time.time()
    is_faithful, final_answer = await check_faithfulness(
        raw_answer,
        retrieved_chunks,
    )
    t_faith_end = time.time()
    print(f"[Chat] Faithfulness check took {t_faith_end - t_faith_start:.2f}s, result: {is_faithful}", flush=True)

    faithfulness_status = "FAITHFUL" if is_faithful else "INSUFFICIENT_EVIDENCE"

    # 8. Build Citations
    citations_data = build_citations(retrieved_chunks)
    print(f"[Chat] Built {len(citations_data)} citations", flush=True)

    # ── Ensure every citation has a document_id ──────────────────────────
    # The chunk metadata often doesn't carry document_id after index reload.
    # Batch-resolve from the database by filename so the frontend's PDF viewer
    # can construct a valid /api/documents/{id}/file URL.
    missing = [c for c in citations_data if not c.get("document_id")]
    if missing:
        filenames = list({c["filename"] for c in missing})
        doc_map = {
            d.filename: d.id
            for d in db.query(Document).filter(Document.filename.in_(filenames)).all()
        }
        for c in missing:
            doc_id = doc_map.get(c["filename"])
            if doc_id:
                c["document_id"] = doc_id
                print(f"[Chat] Resolved document_id={doc_id} for '{c['filename']}'", flush=True)

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

    # Store Citations in DB (using new compact model)
    citation_objs = []
    for c in citations_data:
        doc = db.query(Document).filter(Document.filename == c["filename"]).first()

        cit = Citation(
            message_id=bot_msg.id,
            chunk_id=c.get("chunk_id"),
            document_id=doc.id if doc else None,
            chunk_index=0,
            filename=c["filename"],
            page_number=c["page_number"],
            heading=c.get("heading"),
            section=c.get("section"),
            text_snippet=c.get("text_snippet", ""),
            bbox=c.get("bbox"),          # Single JSON column → {"x0":…, "y0":…, "x1":…, "y1":…}
            page_width=c.get("page_width"),
            page_height=c.get("page_height"),
        )
        db.add(cit)
        citation_objs.append(cit)

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
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "filename": c.filename,
            "page_number": c.page_number,
            "heading": c.heading,
            "section": c.section,
            "text_snippet": c.text_snippet,
            "bbox": c.bbox,  # Single JSON column
            "page_width": c.page_width,
            "page_height": c.page_height,
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
