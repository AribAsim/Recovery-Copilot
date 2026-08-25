from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class PolicyContext(BaseModel):
    current_time: datetime
    high_value_threshold: float = 50000.0
    confidence_threshold: float = 0.70
    max_retry_attempts: int = 3
    operating_window_start_hour: int = 8  # compliance operating window (e.g. 8 AM to 8 PM)
    operating_window_end_hour: int = 20

class RuleEvaluation(BaseModel):
    rule: str
    passed: bool
    detail: str

class PolicyDecision(BaseModel):
    approved_action: str
    original_recommendation: str
    was_overridden: bool
    override_reason: Optional[str] = None
    rules_evaluated: List[RuleEvaluation]
    rules_triggered: List[str]
    blocked: bool

# Explicit ALLOWED_ACTIONS list
ALLOWED_ACTIONS = {
    "retry_payment",
    "retry_after_delay",
    "request_new_payment_method",
    "send_recovery_message",
    "escalate_human",
    "no_action"
}

def evaluate(
    recommendation: Optional[str],
    predicted_probability: Optional[float],
    confidence: Optional[float],
    candidate_actions: Optional[List[Any]],
    transaction: Any,
    context: PolicyContext
) -> PolicyDecision:
    rules_eval: List[RuleEvaluation] = []
    rules_triggered: List[str] = []
    
    # Defaults
    approved_action = recommendation or "escalate_human"
    was_overridden = False
    override_reason = None
    blocked = False

    # 1. Validation of AI Output structure (RULE 6)
    ai_malformed = False
    malformed_detail = ""
    if not recommendation or recommendation not in ALLOWED_ACTIONS:
        ai_malformed = True
        malformed_detail = f"Unknown or missing action: {recommendation}"
    elif predicted_probability is None or not (0.0 <= predicted_probability <= 1.0):
        ai_malformed = True
        malformed_detail = f"Probability out of range: {predicted_probability}"
    elif confidence is None or not (0.0 <= confidence <= 1.0):
        ai_malformed = True
        malformed_detail = f"Confidence out of range: {confidence}"

    rules_eval.append(RuleEvaluation(
        rule="ai_output_format",
        passed=not ai_malformed,
        detail="AI output matches strict schema and valid actions." if not ai_malformed else malformed_detail
    ))

    if ai_malformed:
        rules_triggered.append("ai_output_format")
        return PolicyDecision(
            approved_action="escalate_human",
            original_recommendation=recommendation or "unknown",
            was_overridden=True,
            override_reason=f"AI output rejected: {malformed_detail}",
            rules_evaluated=rules_eval,
            rules_triggered=rules_triggered,
            blocked=True
        )

    # 2. Transaction Eligibility check (RULE 4)
    eligible = transaction.status in ("failed", "pending")
    rules_eval.append(RuleEvaluation(
        rule="transaction_eligible",
        passed=eligible,
        detail=f"Transaction is in recoverable state ({transaction.status})." if eligible else f"Transaction is in terminal state ({transaction.status})."
    ))
    if not eligible:
        rules_triggered.append("transaction_eligible")
        return PolicyDecision(
            approved_action="no_action",
            original_recommendation=recommendation,
            was_overridden=True,
            override_reason="Transaction not in recoverable state.",
            rules_evaluated=rules_eval,
            rules_triggered=rules_triggered,
            blocked=True
        )

    # 3. Max Attempts Enforcement (RULE 1)
    # The actual attempt number being processed is attempts_count + 1
    attempts_exceeded = transaction.attempts_count >= context.max_retry_attempts
    rules_eval.append(RuleEvaluation(
        rule="max_attempts",
        passed=not attempts_exceeded,
        detail=f"Attempt {transaction.attempts_count + 1} of {context.max_retry_attempts} attempts max."
    ))
    if attempts_exceeded:
        rules_triggered.append("max_attempts")
        return PolicyDecision(
            approved_action="escalate_human",
            original_recommendation=recommendation,
            was_overridden=True,
            override_reason="Maximum retry limit reached.",
            rules_evaluated=rules_eval,
            rules_triggered=rules_triggered,
            blocked=True
        )

    # 4. Compliance Window checking (RULE 9)
    current_hour = context.current_time.hour
    within_window = context.operating_window_start_hour <= current_hour < context.operating_window_end_hour
    rules_eval.append(RuleEvaluation(
        rule="compliance_operating_window",
        passed=within_window,
        detail=f"Current hour {current_hour}:00 is within allowed operating window ({context.operating_window_start_hour}:00 - {context.operating_window_end_hour}:00)." if within_window else f"Out of operating window hours: {current_hour}:00"
    ))
    if not within_window:
        rules_triggered.append("compliance_operating_window")
        # Route to escalate_human or delay depending on preference, here delay or no_action is safe
        approved_action = "retry_after_delay"
        was_overridden = True
        override_reason = "Operating hours violation. Automated action scheduled for later."

    # 5. Promise to Pay check (RULE 8)
    has_promise = getattr(transaction, "promise_to_pay", False)
    rules_eval.append(RuleEvaluation(
        rule="promise_to_pay_inactive",
        passed=not has_promise,
        detail="No active customer payment promise outstanding." if not has_promise else "Active customer payment promise exists."
    ))
    if has_promise:
        rules_triggered.append("promise_to_pay_inactive")
        approved_action = "escalate_human"
        was_overridden = True
        override_reason = "Customer has unresolved payment promise. Forcing human routing."

    # 6. High Value limit (RULE 7)
    is_high_value = transaction.amount >= context.high_value_threshold
    rules_eval.append(RuleEvaluation(
        rule="high_value_limit",
        passed=not is_high_value,
        detail=f"Amount ₹{transaction.amount} is below high-value threshold ₹{context.high_value_threshold}." if not is_high_value else f"High value transaction ₹{transaction.amount} matches/exceeded limit ₹{context.high_value_threshold}."
    ))
    if is_high_value:
        rules_triggered.append("high_value_limit")
        approved_action = "escalate_human"
        was_overridden = True
        override_reason = f"High value transaction ₹{transaction.amount} requires human supervision."

    # 7. Repeat failed actions (RULE 3)
    prior_actions = {a.action_taken for a in getattr(transaction, "attempts", []) if a.outcome == "failed"}
    is_repeated_failure = approved_action in prior_actions and approved_action not in ("escalate_human", "no_action")
    rules_eval.append(RuleEvaluation(
        rule="no_repeated_failed_action",
        passed=not is_repeated_failure,
        detail=f"No repeat of previously failed actions." if not is_repeated_failure else f"Action '{approved_action}' previously failed for this transaction."
    ))
    if is_repeated_failure:
        rules_triggered.append("no_repeated_failed_action")
        approved_action = "escalate_human"
        was_overridden = True
        override_reason = f"Duplicate action check failed: '{recommendation}' already failed."

    # 8. Confidence Gate checking (RULE 5)
    confidence_passed = confidence >= context.confidence_threshold
    rules_eval.append(RuleEvaluation(
        rule="confidence_threshold",
        passed=confidence_passed,
        detail=f"AI model confidence {confidence:.2f} satisfies threshold {context.confidence_threshold:.2f}." if confidence_passed else f"AI model confidence {confidence:.2f} below threshold {context.confidence_threshold:.2f}."
    ))
    if not confidence_passed:
        rules_triggered.append("confidence_threshold")
        approved_action = "escalate_human"
        was_overridden = True
        override_reason = f"Predictor confidence {confidence:.2f} too low."

    # 9. Cooldown/Immediate checks (RULE 2)
    # If action is retry_payment (meaning immediate retry) but cooldown restricts it
    # For simulation, say the rule requires that we can't retry_payment on second attempt immediately
    if approved_action == "retry_payment" and transaction.attempts_count > 0:
        rules_eval.append(RuleEvaluation(
            rule="retry_cooldown",
            passed=False,
            detail="Immediate retry not allowed on subsequent attempts. Cooling interval required."
        ))
        rules_triggered.append("retry_cooldown")
        approved_action = "retry_after_delay"
        was_overridden = True
        override_reason = "Immediate retry blocked by cooldown on sequential attempts."
    else:
        rules_eval.append(RuleEvaluation(
            rule="retry_cooldown",
            passed=True,
            detail="Immediate retry cooldown checks passed."
        ))

    return PolicyDecision(
        approved_action=approved_action,
        original_recommendation=recommendation,
        was_overridden=was_overridden,
        override_reason=override_reason,
        rules_evaluated=rules_eval,
        rules_triggered=rules_triggered,
        blocked=len(rules_triggered) > 0 or approved_action != recommendation
    )
