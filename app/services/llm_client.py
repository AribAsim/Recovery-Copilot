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


def generate_message(action: str, amount: float) -> str:
    fallback = TEMPLATES.get(action, "We're following up on your payment.").format(amount=amount)

    if not settings.OPENROUTER_API_KEY:
        return fallback

    prompt = (
        f"Write a single short (max 25 words) professional English customer payment-recovery message "
        f"for action type '{action}' on an amount of Rs.{amount}. "
        f"No greeting, no sign-off, just the message."
    )

    try:
        resp = httpx.post(
            settings.OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 60,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        return content if content else fallback
    except Exception:
        # Never let an LLM/network hiccup break the recovery pipeline
        return fallback
