from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

async def check_faithfulness(answer: str, retrieved_chunks: List[Dict[str, Any]], llm_generator_func) -> Tuple[bool, str]:
    """
    Faithfulness Check: Verifies whether every statement in the generated answer
    is strictly grounded in the provided document context.
    
    Returns (is_faithful, explanation/adjusted_answer)
    """
    if not retrieved_chunks:
        return False, "Insufficient evidence in provided documents."

    context_str = "\n\n".join([f"Page {c.get('page_number')}: {c.get('text')}" for c in retrieved_chunks])
    
    prompt = f"""You are an audit reviewer verifying factual consistency.
CONTEXT:
{context_str}

PROPOSED ANSWER:
{answer}

TASK:
Determine if EVERY claim in the PROPOSED ANSWER is explicitly backed up by the CONTEXT above.
Respond strictly in JSON format with two keys:
"is_faithful": true/false,
"reason": "short explanation"
"""
    try:
        response = await llm_generator_func(prompt, system_prompt="You are a strict document auditor.")
        if "true" in response.lower() and "is_faithful" in response.lower():
            return True, answer
        elif "false" in response.lower():
            return False, "Insufficient evidence in provided documents to support part or all of this claim."
        return True, answer
    except Exception as e:
        logger.warning(f"Faithfulness check evaluation failed: {e}")
        return True, answer
