import os
import logging
import streamlit as st

logger = logging.getLogger(__name__)

def get_secret_val(key_name):
    """Retrieve secret from os.environ or st.secrets safely."""
    if key_name in os.environ and os.environ[key_name].strip():
        return os.environ[key_name].strip()
    try:
        if hasattr(st, "secrets") and key_name in st.secrets and str(st.secrets[key_name]).strip():
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return None

class APIKeyRotator:
    """
    Manages API keys for GROQ, GEMINI, and HF providers with fallback rotation.
    Supports up to 3 API keys per provider (e.g. GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3).
    """

    @staticmethod
    def get_api_keys(provider: str) -> list:
        """Returns all configured non-empty API keys for a provider."""
        provider_upper = provider.upper()
        keys = []
        
        # Check standard key name (e.g., GROQ_API_KEY, GEMINI_API_KEY, HF_API_KEY)
        primary_name = f"{provider_upper}_API_KEY"
        k1 = get_secret_val(primary_name) or get_secret_val(f"{primary_name}_1")
        if k1:
            keys.append(k1)
            
        # Check explicit fallback keys (Key 2 and Key 3)
        for i in range(2, 4):
            key_name = f"{provider_upper}_API_KEY_{i}"
            k = get_secret_val(key_name)
            if k and k not in keys:
                keys.append(k)
                
        return keys

    @classmethod
    def execute_with_fallback(cls, provider: str, call_fn, emergency_fallback_fn=None):
        """
        Executes call_fn(api_key) trying keys 1, 2, 3 in sequence for the specified provider.
        If all keys for provider fail, executes emergency_fallback_fn if provided.
        """
        keys = cls.get_api_keys(provider)
        errors = []

        if not keys:
            logger.warning(f"No API keys configured for provider '{provider}'. Attempting emergency fallback...")
        else:
            for idx, key in enumerate(keys, 1):
                try:
                    logger.info(f"Executing {provider} request using Key {idx}/{len(keys)}...")
                    result = call_fn(key)
                    # Check if result is a dict with success=False and rate limit error
                    if isinstance(result, dict) and not result.get("success", True):
                        err_msg = str(result.get("error", "")).lower()
                        if any(term in err_msg for term in ["rate limit", "quota", "429", "exceeded", "invalid"]):
                            logger.warning(f"{provider} Key {idx} rate limited/failed: {err_msg}. Rotating key...")
                            errors.append(f"Key {idx}: {err_msg}")
                            continue
                    return result
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"{provider} Key {idx} raised error: {err_msg}. Rotating key...")
                    errors.append(f"Key {idx}: {err_msg}")

        # All primary provider keys failed or missing
        if emergency_fallback_fn:
            logger.info(f"All {provider} keys exhausted. Triggering emergency fallback provider...")
            try:
                return emergency_fallback_fn()
            except Exception as ef_err:
                errors.append(f"Emergency fallback failed: {str(ef_err)}")

        return {
            "success": False,
            "error": f"All {provider} API keys exhausted or failed: {'; '.join(errors)}"
        }
