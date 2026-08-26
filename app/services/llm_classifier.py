"""
LLM-based payment failure classifier.

Provider chain:
    OpenRouter -> NVIDIA NIM -> Groq -> deterministic fallback

The LLM is used only for diagnosis.
All returned data is validated before entering the recovery pipeline.
"""

import json
import re
import sys
from typing import Any

import httpx

from app.core.config import settings
from app.services.classifier import classify_failure, KNOWN_CODES
from app.services.llm_client import is_valid_key


# ---------------------------------------------------------------------------
# VALID CLASSIFICATION CATEGORIES
# ---------------------------------------------------------------------------

VALID_CATEGORIES = set(KNOWN_CODES.keys()) | {"unknown"}


# ---------------------------------------------------------------------------
# PROVIDER ERROR LOGGING
# ---------------------------------------------------------------------------

def _log_provider_error(
    provider: dict,
    exc: Exception,
    response_body: str | None = None,
) -> None:
    """
    Log provider failures for server-side diagnostics.

    Never expose API keys or full provider responses.
    """

    status = getattr(getattr(exc, "response", None), "status_code", None)

    message = (
        f"[LLM] provider={provider['name']} "
        f"model={provider['model']} "
        f"error={type(exc).__name__}"
    )

    if status:
        message += f" status={status}"

    print(message, file=sys.stderr)

    if response_body:
        preview = response_body[:1000].replace("\n", " ")

        print(
            f"[LLM] response_preview={preview}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# RESPONSE EXTRACTION
# ---------------------------------------------------------------------------

def _extract_content(data: dict[str, Any]) -> str:
    """
    Extract assistant content from an OpenAI-compatible response.

    Supports:
        choices[0].message.content -> string
        choices[0].message.content -> list of text blocks
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

    # Normal OpenAI-compatible response.
    if isinstance(content, str):
        content = content.strip()

        if content:
            return content

        raise ValueError("LLM response content was empty")

    # Some providers may return structured content blocks.
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

    raise ValueError(
        f"Unsupported LLM content format: {type(content).__name__}"
    )


# ---------------------------------------------------------------------------
# JSON EXTRACTION
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract a JSON object from model output.

    Handles:

        {"category": "...", ...}

    and:

        ```json
        {"category": "...", ...}
        ```

    and models that accidentally prepend explanatory text.
    """

    if not text:
        raise ValueError("LLM returned empty text")

    text = text.strip()

    # Remove markdown fences.
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

    # First attempt: entire response is JSON.
    try:

        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # Second attempt:
    # Find the first JSON object inside surrounding text.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        raise ValueError(
            "LLM response did not contain a JSON object"
        )

    candidate = text[start:end + 1]

    try:

        parsed = json.loads(candidate)

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"LLM JSON parsing failed: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "LLM JSON root must be an object"
        )

    return parsed


# ---------------------------------------------------------------------------
# RESULT VALIDATION
# ---------------------------------------------------------------------------

def _validate_result(
    parsed: dict[str, Any],
) -> tuple[str, float, str]:
    """
    Validate and normalize the model classification.
    """

    # -------------------------
    # Category
    # -------------------------

    category = parsed.get("category")

    if not isinstance(category, str):
        raise ValueError(
            "LLM response missing string category"
        )

    category = category.strip()

    if category not in VALID_CATEGORIES:

        raise ValueError(
            f"Invalid category returned by LLM: {category}"
        )

    # -------------------------
    # Confidence
    # -------------------------

    confidence = parsed.get("confidence")

    try:
        confidence = float(confidence)

    except (TypeError, ValueError) as exc:

        raise ValueError(
            "Invalid confidence returned by LLM"
        ) from exc

    # Clamp confidence to safe range.
    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    # -------------------------
    # Reasoning
    # -------------------------

    reasoning = parsed.get(
        "reasoning",
        "",
    )

    if not isinstance(reasoning, str):
        reasoning = ""

    reasoning = reasoning.strip()

    # Keep stored reasoning small.
    reasoning = reasoning[:500]

    return (
        category,
        confidence,
        reasoning,
    )


# ---------------------------------------------------------------------------
# PROVIDER CONFIGURATION
# ---------------------------------------------------------------------------

def _get_providers() -> list[dict]:
    """
    Build the configured provider fallback chain.
    """

    providers = []

    # Primary: OpenRouter
    if is_valid_key(settings.OPENROUTER_API_KEY):

        providers.append({
            "name": "OpenRouter",
            "url": settings.OPENROUTER_URL,
            "key": settings.OPENROUTER_API_KEY,
            "model": settings.OPENROUTER_MODEL,
        })

    # Fallback 1: NVIDIA NIM
    if is_valid_key(settings.NVIDIA_API_KEY):

        providers.append({
            "name": "NVIDIA NIM",
            "url": settings.NVIDIA_API_URL,
            "key": settings.NVIDIA_API_KEY,
            "model": settings.NVIDIA_MODEL,
        })

    # Fallback 2: Groq
    if is_valid_key(settings.GROQ_API_KEY):

        providers.append({
            "name": "Groq",
            "url": settings.GROQ_API_URL,
            "key": settings.GROQ_API_KEY,
            "model": settings.GROQ_MODEL,
        })

    return providers


# ---------------------------------------------------------------------------
# MAIN CLASSIFIER
# ---------------------------------------------------------------------------

def classify(
    raw_text: str,
    fallback_code: str | None = None,
) -> dict:
    """
    Classify a payment failure using the configured AI provider chain.

    Provider order:

        OpenRouter
            ↓
        NVIDIA NIM
            ↓
        Groq
            ↓
        deterministic classifier

    Returns:

        {
            "diagnosis": str,
            "confidence": float,
            "reasoning": str,
            "raw_reasoning": str,
            "mode_used": str,
            "predictor_status": str,
            "fallback_status": str
        }
    """

    # -----------------------------------------------------------------------
    # Input normalization
    # -----------------------------------------------------------------------

    if not raw_text:
        raw_text = "Unknown error"

    fallback_val = (
        fallback_code
        or "card_declined_generic"
    )

    fallback_res = classify_failure(
        fallback_val
    )

    # -----------------------------------------------------------------------
    # Provider list
    # -----------------------------------------------------------------------

    providers = _get_providers()

    # No AI providers configured.
    if not providers:

        return {
            "diagnosis": fallback_res["diagnosis"],
            "confidence": fallback_res["confidence"],
            "reasoning": (
                "AI prediction unavailable. "
                "A deterministic diagnosis was used."
            ),
            "raw_reasoning": (
                "Fallback used: "
                "no valid AI provider configured."
            ),
            "mode_used": "deterministic_fallback",
            "predictor_status": "fallback",
            "fallback_status": "Active",
            "provider": "deterministic",
        }

    # -----------------------------------------------------------------------
    # Classification prompt
    # -----------------------------------------------------------------------

    categories = ", ".join(
        sorted(VALID_CATEGORIES)
    )

    system_prompt = f"""
You are a payment failure classification system.

Classify the payment failure into exactly ONE of these categories:

{categories}

Return ONLY one JSON object using exactly these fields:

{
  "category": "one allowed category",
  "confidence": 0.0,
  "reasoning": "one short sentence"
}

Rules:

- category MUST exactly match one allowed category.
- confidence MUST be between 0.0 and 1.0.
- reasoning MUST be one short sentence.
- Do NOT provide a thinking process.
- Do NOT provide chain-of-thought.
- Do NOT provide analysis before the JSON.
- Do NOT use Markdown.
- Do NOT use ```json.
- Do NOT include any text before or after the JSON.
"""

    # -----------------------------------------------------------------------
    # Provider fallback chain
    # -----------------------------------------------------------------------

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
                            "Classify this payment failure:\n"
                            f"{raw_text}"
                        ),
                    },
                ],

                # Keep output short.
                "max_tokens": 100,

                # Deterministic generation.
                "temperature": 0,
            }

            # ---------------------------------------------------------------
            # Request
            # ---------------------------------------------------------------

            response = httpx.post(
                provider["url"],

                headers={
                    "Authorization": (
                        f"Bearer {provider['key']}"
                    ),
                    "Content-Type": "application/json",
                },

                json=payload,

                timeout=10.0,
            )

            response_text = response.text

            # HTTP errors.
            response.raise_for_status()

            # ---------------------------------------------------------------
            # Parse provider response
            # ---------------------------------------------------------------

            data = response.json()

            content = _extract_content(
                data
            )

            parsed = _extract_json(
                content
            )

            category, confidence, reasoning = (
                _validate_result(parsed)
            )

            # ---------------------------------------------------------------
            # Successful AI classification
            # ---------------------------------------------------------------

            print(
                f"[LLM] {provider['name']} "
                f"model={provider['model']} "
                f"SUCCESS "
                f"diagnosis={category} "
                f"confidence={confidence:.2f}",
                file=sys.stderr,
            )

            return {
                "diagnosis": category,

                "confidence": confidence,

                "reasoning": (
                    "AI classified the payment failure as "
                    f"{category.replace('_', ' ')}."
                ),

                "raw_reasoning": reasoning,

                "mode_used": "llm",

                "predictor_status": "success",

                "fallback_status": "Inactive",

                "provider": provider["name"],

                "model": provider["model"],
            }

        # ---------------------------------------------------------------
        # Provider failure
        # ---------------------------------------------------------------

        except Exception as exc:

            _log_provider_error(
                provider,
                exc,
                response_body=response_text,
            )

            # Try next provider.
            continue

    # -----------------------------------------------------------------------
    # FINAL DETERMINISTIC FALLBACK
    # -----------------------------------------------------------------------

    print(
        "[LLM] All configured AI providers failed. "
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

        "raw_reasoning": (
            "All configured AI providers failed."
        ),

        "mode_used": "deterministic_fallback",

        "predictor_status": "fallback",

        "fallback_status": "Active",

        "provider": "deterministic",
    }
