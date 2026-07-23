import os
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv
load_dotenv()
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Initialize clients using OpenAI compatible endpoints
nvidia_api_key = os.environ.get("NVIDIA_API_KEY", "")
groq_api_key = os.environ.get("GROQ_API_KEY", "")

nvidia_client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=nvidia_api_key or "dummy-key"
) if nvidia_api_key else None

groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=groq_api_key or "dummy-key"
) if groq_api_key else None

NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"
GROQ_MODEL = "llama-3.3-70b-versatile"

async def generate_llm_text(prompt: str, system_prompt: str = "You are an enterprise AI document assistant.") -> str:
    """
    Generates text using NVIDIA NIM primary, Groq fallback, or intelligent local template generator.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Attempt 1: NVIDIA NIM
    if nvidia_client and nvidia_api_key:
        try:
            logger.info("Calling NVIDIA NIM API...")
            res = await nvidia_client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1024
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"NVIDIA NIM call failed: {e}. Trying Groq fallback...")

    # Attempt 2: Groq Fallback
    if groq_client and groq_api_key:
        try:
            logger.info("Calling Groq API...")
            res = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1024
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")

    # Fallback: Synthesis generator for local development/offline resilience
    return generate_local_response(prompt)


def generate_local_response(prompt: str) -> str:
    """
    Offline/local response synthesised directly from context.

    Parses the ``[Source N: filename | Page P | heading]`` blocks produced
    by `compress_context()` and returns a clean, concise answer with
    ``[N]`` inline citation markers that the frontend renders as clickable
    badges.

    Note
    ----
    Because no remote LLM is available, the "answer" is a structured
    presentation of the relevant source text, not a natural-language
    response.  The frontend citation badges still work for navigation.
    """
    if "CONTEXT:" not in prompt:
        return (
            "DocIntel platform is operational. Upload documents and ask "
            "specific questions to get AI-powered answers with citations."
        )

    # ── Extract context block and user question ────────────────────────
    try:
        context_block = prompt.split("CONTEXT:")[1]
        if "USER QUESTION:" in context_block:
            parts = context_block.split("USER QUESTION:")
            context_text = parts[0].strip()
            user_question = parts[1].strip() if len(parts) > 1 else ""
        else:
            context_text = context_block.strip()
            user_question = ""
    except (IndexError, ValueError):
        context_text = ""
        user_question = prompt

    if not context_text:
        return (
            "I couldn't find any document context to answer your question. "
            "Please try uploading a relevant document first."
        )

    # ── Parse [Source N: filename | Page P | heading] blocks ───────────
    source_pattern = re.compile(
        r'\[Source (\d+):\s*([^|]+)\|\s*Page\s*(\d+)\s*\|\s*([^\]]+)\]\s*\n(.+?)(?=\n\n---\n\n|\Z)',
        re.DOTALL,
    )

    sources = []
    for match in source_pattern.finditer(context_text):
        sources.append({
            "idx": int(match.group(1)),
            "filename": match.group(2).strip(),
            "page": int(match.group(3)),
            "heading": match.group(4).strip(),
            "text": match.group(5).strip(),
        })

    if not sources:
        # Could not parse structured blocks — show raw context as fallback
        clean = re.sub(r'^\[Source[^\]]+\]\s*\n', '', context_text, flags=re.MULTILINE)
        return (
            f"Here is what I found in the retrieved documents:\n\n"
            f"{clean[:600]}{'...' if len(clean) > 600 else ''}"
        )

    # ── Concise answer with inline [1], [2] markers ───────────────────
    evidence = []
    for s in sources:
        text = s["text"]
        snip = text[:400]
        if len(text) > 400:
            snip += "..."
        evidence.append(
            f"[{s['idx']}] From **{s['filename']}** (Page {s['page']}, {s['heading']}):\n"
            f"{snip}"
        )

    # If there's a user question, prepend a brief acknowledgment
    header = f"Based on the document{'' if len(sources) == 1 else 's'} retrieved, "
    if user_question:
        header += f"here is relevant information regarding your query:\n\n"
    else:
        header += f"here are the relevant excerpts:\n\n"

    return header + "\n\n---\n\n".join(evidence)


async def run_guardrails(query: str) -> Tuple[bool, str]:
    """
    Guardrails checking for malicious prompts or off-topic input.
    """
    forbidden_keywords = ["drop database", "sudo rm", "hack", "system bypass"]
    for kw in forbidden_keywords:
        if kw in query.lower():
            return False, "Query blocked by safety guardrails."
    return True, query


async def run_query_rewrite(query: str) -> str:
    """
    Rewrites user query to optimize hybrid vector & keyword retrieval.

    Previously appended generic technical jargon ("detailed specifications
    technical document parameters") to short queries, which biased results
    toward technical manuals and made the system useless for non-technical
    content like resumes, HR documents, or general business files.

    Now simply returns the original query unchanged — modern embedding
    models (BGE / all-MiniLM) handle short queries well, and BM25 keyword
    matching works naturally without artificial expansion.
    """
    return query


def build_citations(
    retrieved_chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build structured citation objects from retrieved chunks.

    Every citation is backed by:
    * ``chunk_db_id`` — the database primary key of ``DocumentChunk``,
      allowing the frontend or API consumer to resolve full chunk data.
    * ``bbox`` — real bounding-box coordinates from the parser (not synthetic).
      When a chunk spans multiple blocks the first block's bbox is used.
    * ``page_width`` / ``page_height`` — for accurate coordinate scaling
      in the frontend PDF viewer.

    Chunks with identical ``(filename, page, heading, text[:50])`` are
    deduplicated to avoid showing the same evidence twice.
    """
    citations: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for idx, chunk in enumerate(retrieved_chunks):
        meta = chunk.get("metadata", {})
        filename = meta.get("filename", "Document")
        page = chunk.get("page_number", 1)
        heading = chunk.get("heading", "Section")
        text = chunk.get("text", "")
        bbox = chunk.get("bbox", None)

        dedup_key = (filename, page, heading, text[:50])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # ── Real bounding box (only when the parser provided coordinates) ──
        bbox_dict: dict[str, int] | None = None
        if bbox and len(bbox) == 4:
            try:
                bbox_dict = {
                    "x0": int(bbox[0]),
                    "y0": int(bbox[1]),
                    "x1": int(bbox[2]),
                    "y1": int(bbox[3]),
                }
            except (TypeError, ValueError):
                bbox_dict = None

        # Page dimensions for frontend coordinate scaling
        page_w: float | None = None
        page_h: float | None = None
        if bbox_dict:
            page_w = meta.get("_page_width")
            page_h = meta.get("_page_height")

        citations.append(
            {
                "citation_id": f"cit_{idx + 1}",
                "chunk_id": meta.get("chunk_db_id"),
                "document_id": meta.get("document_id"),
                "filename": filename,
                "page_number": page,
                "heading": heading,
                "section": chunk.get("section", f"Page {page}"),
                "text_snippet": text[:250] + ("..." if len(text) > 250 else ""),
                "bbox": bbox_dict,
                "page_width": page_w,
                "page_height": page_h,
            }
        )

    return citations
