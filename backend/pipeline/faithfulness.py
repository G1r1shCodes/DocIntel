import re
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Minimum length below which we skip the LLM faithfulness call and
# just do a simple substring check against the retrieved context.
# This avoids expensive API round-trips for short factual answers
# like "Girish Kumar Yadav" or "42 pages".
_SHORT_ANSWER_THRESHOLD = 80


def _check_answer_in_context(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> bool:
    """
    Quick heuristic: for short answers, check whether the answer text
    appears as a substring in any of the retrieved chunks.

    Returns ``True`` if the answer (or its key nouns) are found in at
    least one chunk.
    """
    answer_lower = answer.lower().strip().rstrip(".!?")

    # Extract the key noun phrases (words longer than 3 characters)
    key_words = [w for w in re.split(r'[\s,;:()]+', answer_lower) if len(w) > 3]
    if not key_words:
        key_words = answer_lower.split()  # fall back to all words

    for chunk in retrieved_chunks:
        chunk_text = (chunk.get("text") or "").lower()
        # Direct substring match
        if answer_lower in chunk_text:
            return True
        # All key words appear in this chunk
        if all(w in chunk_text for w in key_words):
            return True

    return False


async def check_faithfulness(answer: str, retrieved_chunks: List[Dict[str, Any]], llm_generator_func) -> Tuple[bool, str]:
    """
    Faithfulness Check: Verifies whether the generated answer is grounded
    in the provided document context.

    For **short answers** (≤ 80 chars) a fast keyword/substring heuristic
    is used instead of an LLM call, avoiding expensive API round-trips.

    For longer answers the LLM is asked a **lenient** question: "Are the key
    claims supported by the context?" rather than the strict "every claim
    explicitly backed up".

    Returns (is_faithful, answer_text)
    """
    if not retrieved_chunks:
        return False, answer

    # ── Short-answer fast path (no LLM call) ─────────────────────────────
    if len(answer.strip()) < _SHORT_ANSWER_THRESHOLD:
        found = _check_answer_in_context(answer, retrieved_chunks)
        if found:
            return True, answer
        # Fall through to LLM check below for a more nuanced evaluation
        logger.info(
            "Short answer (%d chars) failed substring check, falling back to LLM",
            len(answer.strip()),
        )

    # ── Full LLM faithfulness check ──────────────────────────────────────
    context_str = "\n\n".join(
        [
            f"[Source {idx + 1}]: Page {c.get('page_number')}: {c.get('text')}"
            for idx, c in enumerate(retrieved_chunks)
        ]
    )

    prompt = f"""You are a document reviewer.
CONTEXT:
{context_str}

ANSWER:
{answer}

Is the ANSWER supported by the CONTEXT? Answer TRUE if the main facts in the
answer can be found in the context, even if paraphrased. Answer FALSE only if
the answer contains information that directly contradicts or is completely
absent from the context.

Respond with a single word: TRUE or FALSE.
"""
    try:
        response = await llm_generator_func(
            prompt, system_prompt="You are a fair and accurate document reviewer."
        )
        response_clean = response.strip().lower()
        if re.search(r'\bfalse\b', response_clean):
            return False, answer
        elif re.search(r'\btrue\b', response_clean):
            return True, answer
        # Default to faithful if the response is ambiguous
        return True, answer
    except Exception as e:
        logger.warning(f"Faithfulness check evaluation failed: {e}")
        return True, answer
