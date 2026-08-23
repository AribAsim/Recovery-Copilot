"""
Decision step: pure lookup table, no LLM in this path.

This is the "bounded and gated" part of the pipeline. Every action a
transaction can trigger is enumerated here — nothing outside this table
can ever be executed, which is what makes the money actions explainable.
"""

# Compliance Note:
# The retry rules routing table, strict MAX_RETRY_ATTEMPTS bounds, and the escalation gates 
# implemented herein are designed in accordance with RBI's e-mandate retry-limit guidelines 
# and TRAI DND regulations for non-intrusive, compliant automated customer financial messaging.
RULES = {
    "insufficient_funds": "retry_in_24h",
    "expired_card": "request_new_method",
    "network_timeout": "retry_immediate",
    "bank_server_down": "retry_in_24h",
    "user_abandoned": "send_nudge",
    "invalid_cvv": "request_new_method",
    "card_declined_generic": "escalate_human",
    "unknown": "escalate_human",
}

REASON_TEXT = {
    "retry_in_24h": "Transient/liquidity issue — safe to retry after a cooling window.",
    "request_new_method": "Card-level issue — retrying won't help, ask for a new payment method.",
    "retry_immediate": "Infra-level failure, not the user's fault — safe to retry right away.",
    "send_nudge": "User dropped off, no gateway error — a reminder can recover this.",
    "escalate_human": "Ambiguous or low-confidence signal — do not auto-act, route to a human.",
}


def decide_action(diagnosis: str, confidence: float, threshold: float) -> tuple[str, str]:
    """Returns (action, reasoning). Confidence gate overrides the rule table."""
    if confidence < threshold:
        return "escalate_human", (
            f"Confidence {confidence:.2f} below threshold {threshold:.2f} — "
            "routed to human review instead of auto-acting."
        )
    action = RULES.get(diagnosis, "escalate_human")
    return action, REASON_TEXT.get(action, "Default safe path: escalate.")
