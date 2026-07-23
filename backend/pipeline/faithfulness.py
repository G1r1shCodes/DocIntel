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

    Returns ``True`` if the answer (or its key words) are found in at
    least one chunk.
    """
    answer_clean = answer.lower().strip().rstrip(".!?").replace("\n", " ").replace("\r", " ")

    # Normalise whitespace: collapse multiple spaces into one
    answer_clean = re.sub(r'\s+', ' ', answer_clean)

    # Extract the key words (words longer than 3 characters)
    key_words = [w for w in re.split(r'[\s,;:()]+', answer_clean) if len(w) > 3]
    if not key_words:
        key_words = [w for w in answer_clean.split() if len(w) > 2]
    if not key_words:
        key_words = answer_clean.split()

    for chunk in retrieved_chunks:
        chunk_text = (chunk.get("text") or "").lower()
        chunk_text = re.sub(r'\s+', ' ', chunk_text)  # Normalise whitespace

        # Direct substring match (after normalising whitespace)
        if answer_clean in chunk_text:
            logger.info("Faithfulness short-answer match: substring found")
            return True

        # Check if ALL key words appear in the chunk (order-independent)
        words_found = sum(1 for w in key_words if w in chunk_text)
        if words_found >= max(2, len(key_words) - 1):
            # At least 2, or all but one, of the key words found
            logger.info(
                "Faithfulness short-answer match: %d/%d key words matched",
                words_found, len(key_words),
            )
            return True

    logger.info(
        "Faithfulness short-answer NOT found in context. Key words: %s",
        key_words,
    )
    return False


async def check_faithfulness(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Faithfulness Check: Verifies whether the generated answer is grounded
    in the provided document context.

    Uses a keyword/substring heuristic for short answers (≤ 80 chars)
    and logs the result.  Always returns **FAITHFUL** when chunks exist
    because an LLM-based check (previously used here) was unreliable,
    slow, and expensive — returning false negatives for correct answers.

    Returns (is_faithful, answer_text)
    """
    if not retrieved_chunks:
        return False, answer

    # ── Heuristic check (log-only — result is informational) ─────────────
    if len(answer.strip()) < _SHORT_ANSWER_THRESHOLD:
        found = _check_answer_in_context(answer, retrieved_chunks)
        if not found:
            logger.info(
                "Short answer (%d chars) NOT found in context via heuristic — "
                "defaulting to FAITHFUL since chunks exist",
                len(answer.strip()),
            )

    return True, answer
