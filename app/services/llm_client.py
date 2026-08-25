"""
LLM usage is scoped to ONE narrow job: writing the customer-facing recovery
message. It never decides which action to take — that stays rule-based
(see decision_router.py) so the money-logic remains deterministic/auditable.

Uses OpenRouter (free-tier models). If no API key is set or the call fails,
falls back to a template message so the pipeline never breaks/stalls during
a live demo.
"""

import httpx

from app.core.config import settings

TEMPLATES = {
    "retry_in_24h": "We'll retry your payment of Rs.{amount} in 24 hours. No action needed.",
    "request_new_method": "Your payment of Rs.{amount} needs a different card/UPI. Tap to update: [link]",
    "retry_immediate": "Retrying your payment of Rs.{amount} now due to a temporary network issue.",
    "send_nudge": "Your payment of Rs.{amount} is still pending. Tap here to complete it: [link]",
    "escalate_human": "Your payment of Rs.{amount} needs manual review. Our team will reach out shortly.",
}


def is_valid_key(key: str) -> bool:
    if not key or not key.strip():
        return False
    normalized = key.strip().lower()
    return "your_" not in normalized and "placeholder" not in normalized


def generate_message(action: str, amount: float) -> str:
    fallback = TEMPLATES.get(action, "We're following up on your payment.").format(amount=amount)

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
        return fallback

    prompt = (
        f"Write a single short (max 25 words) professional English customer payment-recovery message "
        f"for action type '{action}' on an amount of Rs.{amount}. "
        f"No greeting, no sign-off, just the message."
    )

    for provider in providers:
        try:
            resp = httpx.post(
                provider["url"],
                headers={"Authorization": f"Bearer {provider['key']}"},
                json={
                    "model": provider["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 60,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if content:
                return content
        except Exception:
            # Fallback to the next provider in the chain
            continue

    return fallback

