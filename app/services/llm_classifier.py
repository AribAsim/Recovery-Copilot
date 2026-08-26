"""
LLM-based payment failure classifier.

Provider chain:
    OpenRouter -> NVIDIA NIM -> Groq -> deterministic fallback

The provider layer is treated as untrusted input:
- responses are validated before use
- malformed responses are rejected
- provider errors never leak into user-facing reasoning
- deterministic classification remains the final safety fallback
"""

import json
import re
import sys
from typing import Any

import httpx

from app.core.config import settings
from app.services.classifier import classify_failure, KNOWN_CODES
from app.services.llm_client import is_valid_key


VALID_CATEGORIES = set(KNOWN_CODES.keys()) | {"unknown"}


def _log_provider_error(provider: dict, exc: Exception, response_body: str | None = None):
    """Log useful diagnostics without exposing them to the audit trail."""

    status = getattr(getattr(exc, "response", None), "status_code", None)

    msg = (
        f"[LLM] provider_model={provider['model']} "
        f"error={type(exc).__name__}"
    )

    if status:
        msg += f" status={status}"

    print(msg, file=sys.stderr)

    if response_body:
        # Keep logs useful but bounded.
        safe_body = response_body[:1000].replace("\n", " ")
        print(
            f"[LLM] response_preview={safe_body}",
            file=sys.stderr,
        )


def _extract_content(data: dict[str, Any]) -> str:
    """
    Extract assistant content from an OpenAI-compatible response.
    Raises ValueError when the structure is unusable.
    """

    choices = data.get("choices")

    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response contained no choices")

    message = choices[0].get("message")

    if not isinstance(message, dict):
        raise ValueError("LLM response contained no valid message")

    content = message.get("content")

    if content is None:
        raise ValueError("LLM response contained empty content")

    # Some providers may return structured content instead of a plain string.
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)

        result = "".join(parts).strip()

        if result:
            return result

    raise ValueError("LLM response content had an unsupported format")


def _extract_json(text: str) -> dict[str, Any]:
    """
    Parse JSON returned by the model.

    Accepts:
    1. Plain JSON
    2. ```json ... ``` fenced JSON
    3. JSON embedded around minor surrounding text
    """

    text = text.strip()

    # Remove markdown code fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    try:
        parsed = json.loads(text)

        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON root was not an object")

        return parsed

    except json.JSONDecodeError:
        # Try extracting the first JSON object.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise ValueError("LLM response did not contain valid JSON")

        candidate = text[start:end + 1]

        parsed = json.loads(candidate)

        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON root was not an object")

        return parsed


def _validate_result(parsed: dict[str, Any]) -> tuple[str, float, str]:
    """Validate and normalize the model's classification."""

    category = parsed.get("category")

    if not isinstance(category, str):
        raise ValueError("Missing category")

    category = category.strip()

    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category returned by LLM: {category}"
        )

    confidence = parsed.get("confidence")

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        raise ValueError("Invalid confidence returned by LLM")

    confidence = max(0.0, min(1.0, confidence))

    reasoning = parsed.get("reasoning", "")

    if not isinstance(reasoning, str):
        reasoning = ""

    return category, confidence, reasoning.strip()


def classify(raw_text: str, fallback_code: str | None = None) -> dict:
    """
    Classify a payment failure using the configured LLM provider chain.

    Returns a clean structured result.
    """

    if not raw_text:
        raw_text = "Unknown error"

    fallback_val = fallback_code or "card_declined_generic"
    fallback_res = classify_failure(fallback_val)

    providers = []

    if is_valid_key(settings.OPENROUTER_API_KEY):
        providers.append({
            "name": "OpenRouter",
            "url": settings.OPENROUTER_URL,
            "key": settings.OPENROUTER_API_KEY,
            "model": settings.OPENROUTER_MODEL,
        })

    if is_valid_key(settings.NVIDIA_API_KEY):
        providers.append({
            "name": "NVIDIA NIM",
            "url": settings.NVIDIA_API_URL,
            "key": settings.NVIDIA_API_KEY,
            "model": settings.NVIDIA_MODEL,
        })

    if is_valid_key(settings.GROQ_API_KEY):
        providers.append({
            "name": "Groq",
            "url": settings.GROQ_API_URL,
            "key": settings.GROQ_API_KEY,
            "model": settings.GROQ_MODEL,
        })

    if not providers:
        return {
            "diagnosis": fallback_res["diagnosis"],
            "confidence": fallback_res["confidence"],
            "reasoning": (
                "AI prediction unavailable. "
                "A deterministic diagnosis was used."
            ),
            "raw_reasoning": "Fallback used: no valid AI provider configured.",
            "mode_used": "deterministic_fallback",
            "predictor_status": "fallback",
            "fallback_status": "Active",
        }

    system_prompt = f"""
You are a payment failure classification system.

Classify the payment failure into exactly ONE of these categories:

{", ".join(sorted(VALID_CATEGORIES))}

Return ONLY a JSON object:

{{
  "category": "one allowed category",
  "confidence": 0.0,
  "reasoning": "short explanation"
}}

Rules:
- category MUST exactly match one of the allowed categories.
- confidence MUST be between 0.0 and 1.0.
- reasoning must be concise.
- Do not include markdown.
- Do not include additional fields.
"""

    for provider in providers:

        response_text = None

        try:
            payload = {
                "model": provider["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt.strip(),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyze this payment failure:\n"
                            f"{raw_text}"
                        ),
                    },
                ],
                "max_tokens": 200,
                "temperature": 0,
            }

            # Do NOT force response_format here.
            # Different providers/models handle it differently.
            resp = httpx.post(
                provider["url"],
                headers={
                    "Authorization": f"Bearer {provider['key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10.0,
            )

            response_text = resp.text

            resp.raise_for_status()

            data = resp.json()

            content = _extract_content(data)

            parsed = _extract_json(content)

            category, confidence, raw_reasoning = _validate_result(
                parsed
            )

            print(
                f"[LLM] {provider['name']} "
                f"({provider['model']}) → SUCCESS "
                f"diagnosis={category} "
                f"confidence={confidence:.2f}",
                file=sys.stderr,
            )

            return {
                "diagnosis": category,
                "confidence": confidence,
                "reasoning": (
                    f"AI classified the payment failure as "
                    f"{category.replace('_', ' ')}."
                ),
                "raw_reasoning": raw_reasoning,
                "mode_used": "llm",
                "predictor_status": "success",
                "fallback_status": "Inactive",
                "provider": provider["name"],
            }

        except Exception as exc:
            _log_provider_error(
                provider,
                exc,
                response_body=response_text,
            )
            continue

    # All configured AI providers failed.
    print(
        "[LLM] All configured providers failed. "
        "Using deterministic fallback.",
        file=sys.stderr,
    )

    return {
        "diagnosis": fallback_res["diagnosis"],
        "confidence": fallback_res["confidence"],
        "reasoning": (
            "AI prediction was unavailable. "
            "A deterministic diagnosis was used."
        ),
        "raw_reasoning": "All configured AI providers failed.",
        "mode_used": "deterministic_fallback",
        "predictor_status": "fallback",
        "fallback_status": "Active",
    }
