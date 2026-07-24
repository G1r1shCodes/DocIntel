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


REFUSAL_PHRASES = [
    "not found", "cannot find", "not mentioned", "no information", "does not contain",
    "does not state", "not provided", "unspecified", "not listed", "no mention"
]


async def check_faithfulness(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Anti-Hallucination & Faithfulness Guardrail:
    Verifies whether the generated answer is strictly grounded in the retrieved document context.

    Checks:
    1. Entity & Numeric Verification (numbers, dates, currency, percentages)
    2. Substring & Keyword Grounding Ratio
    3. Non-hallucinatory refusal detection

    Returns (is_faithful: bool, final_answer: str)
    """
    if not retrieved_chunks:
        return False, answer

    answer_clean = answer.strip()
    answer_lower = answer_clean.lower()

    # 1. If LLM correctly refused to invent facts, it is FAITHFUL
    if any(phrase in answer_lower for phrase in REFUSAL_PHRASES):
        logger.info("[Hallucination Guardrail] Answer is a valid refusal — marked as FAITHFUL.")
        return True, answer_clean

    # Combine all retrieved context text into one normalized string
    context_text = " ".join([c.get("text", "") for c in retrieved_chunks]).lower()
    context_norm = re.sub(r'\s+', ' ', context_text)

    # 2. Numeric & Figure Hallucination Verification
    # Extract numbers/dates/currency/percentages (e.g. 2027, $500, 95%, 42)
    numbers_in_answer = set(re.findall(r'\b\$?\d+(?:\.\d+)?%?\b', answer_clean))
    
    hallucinated_figures = []
    for num in numbers_in_answer:
        # Skip single digit numbers (1-9) often used for formatting or bullet points
        if len(num) == 1 and num in "123456789":
            continue
        if num.lower() not in context_norm:
            hallucinated_figures.append(num)

    if hallucinated_figures:
        logger.warning(f"[Hallucination Guardrail] DETECTED HALLUCINATION! Unbacked figures in answer: {hallucinated_figures}")
        print(f"[Hallucination Guardrail] Flagged unbacked figures: {hallucinated_figures}", flush=True)
        return False, answer_clean

    # 3. Grounding Ratio Check (N-gram / Keyword Overlap)
    words = [w for w in re.split(r'[\s,;:().!?"\']+', answer_lower) if len(w) > 3]
    if not words:
        return True, answer_clean

    matched_words = sum(1 for w in words if w in context_norm)
    grounding_ratio = matched_words / len(words)

    logger.info(f"[Hallucination Guardrail] Grounding ratio: {grounding_ratio:.2f} ({matched_words}/{len(words)} key words matched)")

    if grounding_ratio < 0.35:
        logger.warning(f"[Hallucination Guardrail] DETECTED UNGROUNDED CLAIM! Grounding ratio {grounding_ratio:.2f} < 0.35")
        print(f"[Hallucination Guardrail] Flagged ungrounded claim (ratio {grounding_ratio:.2f})", flush=True)
        return False, answer_clean

    return True, answer_clean
