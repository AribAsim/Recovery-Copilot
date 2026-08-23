"""
Diagnosis step.

Deterministic by design: failure codes from a payment gateway are already
structured data, so we do NOT need an LLM to classify them. This keeps the
money-decision path auditable and removes LLM cost/latency from the hot path.

Each diagnosis returns a confidence score. Low-confidence cases are routed
to human escalation instead of being auto-actioned (see engine.py).
"""

KNOWN_CODES = {
    "insufficient_funds": 0.95,
    "expired_card": 0.95,
    "network_timeout": 0.90,
    "bank_server_down": 0.85,
    "user_abandoned": 0.70,
    "invalid_cvv": 0.90,
    "card_declined_generic": 0.55,   # ambiguous — low confidence on purpose
}

DEFAULT_CONFIDENCE = 0.40  # unseen/unknown code -> force human review


def classify_failure(failure_code: str) -> dict:
    code = failure_code.strip().lower()
    confidence = KNOWN_CODES.get(code, DEFAULT_CONFIDENCE)
    return {
        "diagnosis": code if code in KNOWN_CODES else "unknown",
        "confidence": confidence,
    }
