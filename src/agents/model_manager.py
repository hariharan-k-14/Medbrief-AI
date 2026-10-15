import groq
import logging
import time
from utils.key_fallback_manager import APIKeyRotator

logger = logging.getLogger(__name__)

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "groq/compound"
]

class ModelManager:
    """
    Manages Report Summary Generation exclusively via Groq models.
    Supports 3 Groq API keys with fallback rotation and emergency fallback to Hugging Face.
    """

    def generate_analysis(self, data, system_prompt=None):
        """
        Generate medical report analysis/summary using Groq AI.
        Rotates through up to 3 Groq API keys if rate limits or quota errors occur.
        Falls back to Hugging Face models if all Groq keys are exhausted.
        """
        if not system_prompt or not isinstance(system_prompt, str):
            try:
                from config.prompts import SPECIALIST_PROMPTS
                system_prompt = SPECIALIST_PROMPTS.get("comprehensive_analyst", "You are an expert medical analyst.")
            except Exception:
                system_prompt = "You are an expert medical analyst."

        user_content = str(data) if data is not None else ""

        def call_groq(api_key):
            client = groq.Groq(api_key=api_key)
            last_error = None

            for model in GROQ_MODELS:
                try:
                    logger.info(f"Attempting Groq summary generation with model: {model}")
                    completion = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    return {
                        "success": True,
                        "content": completion.choices[0].message.content,
                        "model_used": f"Groq ({model})",
                        "provider": "Groq"
                    }
                except Exception as e:
                    err_str = str(e).lower()
                    last_error = str(e)
                    if "rate limit" in err_str or "quota" in err_str or "429" in err_str:
                        logger.warning(f"Groq model {model} rate limited: {err_str}. Trying next Groq model...")
                        time.sleep(1)
                        continue
                    else:
                        logger.warning(f"Groq model {model} error: {err_str}")
                        break

            return {"success": False, "error": f"Groq key error: {last_error}"}

        def emergency_hf_fallback():
            logger.info("Triggering Hugging Face emergency fallback for report summary...")
            
            def call_hf(hf_key):
                try:
                    from huggingface_hub import InferenceClient
                    client = InferenceClient(provider="hf-inference", api_key=hf_key)
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ]
                    response = client.chat.completions.create(
                        model="meta-llama/Llama-3.2-3B-Instruct",
                        messages=messages,
                        max_tokens=2000,
                        temperature=0.7
                    )
                    return {
                        "success": True,
                        "content": response.choices[0].message.content,
                        "model_used": "Hugging Face (Llama-3.2-3B-Instruct)",
                        "provider": "HuggingFace"
                    }
                except Exception as hf_err:
                    return {"success": False, "error": f"HF error: {str(hf_err)}"}

            return APIKeyRotator.execute_with_fallback("HF", call_hf)

        # Execute Groq key fallback chain (Key 1 -> Key 2 -> Key 3 -> HF Emergency Fallback)
        return APIKeyRotator.execute_with_fallback(
            provider="GROQ",
            call_fn=call_groq,
            emergency_fallback_fn=emergency_hf_fallback
        )
