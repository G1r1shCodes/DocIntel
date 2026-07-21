import os
from openai import AsyncOpenAI
import logging

# Initialize clients using OpenAI compatible endpoints
# Ensure these environment variables are set:
# NVIDIA_API_KEY, GROQ_API_KEY
nvidia_client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY", "dummy-nvidia-key")
)

groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY", "dummy-groq-key")
)

# You can choose specific models here
NVIDIA_MODEL = "meta/llama3-70b-instruct"
GROQ_MODEL = "llama3-70b-8192"

async def generate_response(prompt: str, system_prompt: str = "You are a helpful assistant."):
    """
    Generates a response using NVIDIA NIM with a fallback to Groq.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    try:
        logging.info("Attempting generation with NVIDIA NIM...")
        response = await nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.warning(f"NVIDIA NIM failed: {e}. Falling back to Groq API...")
        try:
            response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as groq_e:
            logging.error(f"Groq Fallback also failed: {groq_e}")
            raise Exception("All LLM providers failed.")

async def verify_faithfulness(answer: str, context: str):
    """
    Uses the LLM to verify if the generated answer is faithful to the context.
    """
    verification_prompt = (
        f"Context: {context}\n\n"
        f"Answer: {answer}\n\n"
        "Based on the context provided, is the answer fully supported by the context without hallucinating information? "
        "Reply with only 'YES' or 'NO'."
    )
    
    result = await generate_response(verification_prompt, system_prompt="You are a strict evaluator.")
    return result.strip().upper() == "YES"
