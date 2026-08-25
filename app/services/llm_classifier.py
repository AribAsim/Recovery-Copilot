"""
LLM-based classifier using OpenRouter and structured JSON output.
Falls back to deterministic classifier if LLM fails/times out.
"""

import json
import httpx
from app.core.config import settings
from app.services.classifier import classify_failure, KNOWN_CODES
from app.services.llm_client import is_valid_key

VALID_CATEGORIES = list(KNOWN_CODES.keys()) + ["unknown"]


def classify(raw_text: str, fallback_code: str | None = None) -> dict:
    """
    Sends raw_failure_text to OpenRouter to classify the failure category.
    Returns: { "diagnosis": str, "confidence": float, "reasoning": str }
    """
    if not raw_text:
        raw_text = "Unknown error"

    fallback_val = fallback_code or "card_declined_generic"
    fallback_res = classify_failure(fallback_val)
    
    # Check for API keys and build provider list
    providers = []
    if is_valid_key(settings.OPENROUTER_API_KEY):
        providers.append({
            "url": settings.OPENROUTER_URL,
            "key": settings.OPENROUTER_API_KEY,
            "model": settings.OPENROUTER_MODEL
        })
    if is_valid_key(settings.NVIDIA_API_KEY):
        providers.append({
            "url": settings.NVIDIA_API_URL,
            "key": settings.NVIDIA_API_KEY,
            "model": settings.NVIDIA_MODEL
        })
    if is_valid_key(settings.GROQ_API_KEY):
        providers.append({
            "url": settings.GROQ_API_URL,
            "key": settings.GROQ_API_KEY,
            "model": settings.GROQ_MODEL
        })

    if not providers:
        return {
            "diagnosis": fallback_res["diagnosis"],
            "confidence": fallback_res["confidence"],
            "reasoning": "AI prediction unavailable — deterministic fallback used.",
            "raw_reasoning": "Fallback used (missing API key).",
            "mode_used": "deterministic_fallback",
            "predictor_status": "fallback",
            "fallback_status": "Active"
        }

    # Prompt explaining the task and structure
    system_prompt = (
        f"You are a payment failure analysis assistant. Classify the user's payment failure text into one of these exact categories: "
        f"{', '.join(VALID_CATEGORIES)}.\n"
        f"Return JSON matching this schema: "
        f"{{\"category\": \"string\", \"confidence\": float (between 0.0 and 1.0), \"reasoning\": \"string\"}}"
    )
    
    for provider in providers:
        # We want a response format of type json_object
        try:
            resp = httpx.post(
                provider["url"],
                headers={
                    "Authorization": f"Bearer {provider['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": provider["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze this raw failure text: '{raw_text}'"}
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 150,
                },
                timeout=6.0,
            )
            resp.raise_for_status()
            data = resp.json()
            
            choices = data.get("choices", [])
            if not choices:
                raise ValueError(f"No choices in response: {data}")
                
            message = choices[0].get("message", {})
            content = message.get("content")
            if content is None:
                raise ValueError(f"Content is None: {message}")
                
            content = content.strip()
            parsed = json.loads(content)
            category = parsed.get("category", "unknown")
            confidence = parsed.get("confidence", 0.0)
            reasoning = parsed.get("reasoning", "No reasoning provided by LLM.")
            
            # Whitelist validation
            if category not in VALID_CATEGORIES:
                category = "unknown"
                confidence = 0.0
                reasoning = f"LLM returned invalid category '{category}'. Forced to unknown."
                
            return {
                "diagnosis": category,
                "confidence": float(confidence),
                "reasoning": f"AI classified the payment failure as {category.replace('_', ' ')} based on gateway error messages.",
                "raw_reasoning": reasoning, # internal detailed chain/reasoning from LLM
                "mode_used": "llm",
                "predictor_status": "success",
                "fallback_status": "Inactive"
            }
        except Exception as e:
            import sys
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            status_info = f" (HTTP {status})" if status else ""
            print(f"Internal classifier error logged for model {provider['model']}: {type(e).__name__}{status_info}", file=sys.stderr)
            continue
            
    # Fallback to deterministic classifier on closest-matching clean failure_code if all providers failed
    return {
        "diagnosis": fallback_res["diagnosis"],
        "confidence": fallback_res["confidence"],
        "reasoning": "AI prediction unavailable — deterministic fallback used.",
        "raw_reasoning": "Fallback used.",
        "mode_used": "deterministic_fallback",
        "predictor_status": "fallback",
        "fallback_status": "Active"
    }

