import random

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Transaction, RecoveryAttempt
from app.services.classifier import classify_failure
from app.services.decision_router import decide_action
from app.services.llm_client import generate_message

# Actions that plausibly "succeed" in our simulation (vs pure infra retries)
SIMULATED_SUCCESS_RATE = {
    "retry_in_24h": 0.55,
    "request_new_method": 0.65,
    "retry_immediate": 0.50,
    "send_nudge": 0.35,
    "escalate_human": 0.20,
}


def process_transaction(db: Session, txn: Transaction, confidence_threshold: float | None = None) -> RecoveryAttempt:
    """Runs ONE recovery attempt for a transaction and persists the audit trail."""

    # --- Stopping rule guard ---
    if txn.attempts_count >= settings.MAX_RETRY_ATTEMPTS:
        last_action = txn.attempts[-1].action_taken if txn.attempts else ""
        txn.status = "escalated" if last_action == "escalate_human" else "lost"
        db.commit()
        attempt = RecoveryAttempt(
            transaction_id=txn.id,
            attempt_number=txn.attempts_count + 1,
            diagnosis="stopping_rule_triggered",
            confidence=1.0,
            action_taken="give_up",
            reasoning=f"Max attempts ({settings.MAX_RETRY_ATTEMPTS}) reached — stopping to avoid spamming customer.",
            cost=0.0,
            outcome="escalated" if txn.status == "escalated" else "lost",
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return attempt

    # --- Diagnose ---
    diag = classify_failure(txn.failure_code)

    # --- Decide (confidence-gated, rule-based) ---
    threshold = confidence_threshold if confidence_threshold is not None else settings.CONFIDENCE_THRESHOLD
    action, reasoning = decide_action(diag["diagnosis"], diag["confidence"], threshold)

    # --- Self-check: don't repeat an action that already failed for this txn ---
    prior_actions = {a.action_taken for a in txn.attempts}
    if action in prior_actions and action not in ("escalate_human", "give_up"):
        action = "escalate_human"
        reasoning += " | Self-check: this action already failed before, escalating instead of repeating it."

    # --- Execute (simulated) ---
    cost = settings.ACTION_COST.get(action, 0.0)
    escalated = action == "escalate_human"

    if action == "escalate_human":
        outcome = "escalated"
    else:
        success_p = SIMULATED_SUCCESS_RATE.get(action, 0.3)
        outcome = "recovered" if random.random() < success_p else "failed"

    message = generate_message(action, txn.amount) if action in (
        "send_nudge", "request_new_method"
    ) else None

    # --- Persist audit trail ---
    attempt = RecoveryAttempt(
        transaction_id=txn.id,
        attempt_number=txn.attempts_count + 1,
        diagnosis=diag["diagnosis"],
        confidence=diag["confidence"],
        action_taken=action,
        reasoning=reasoning + (f" | Message sent: \"{message}\"" if message else ""),
        cost=cost,
        outcome=outcome,
        escalated=escalated,
    )
    db.add(attempt)

    txn.attempts_count += 1
    if outcome == "recovered":
        txn.status = "recovered"
        if action == "send_nudge":
            txn.promise_to_pay = True
            txn.promised_amount = txn.amount
    elif txn.attempts_count >= settings.MAX_RETRY_ATTEMPTS and outcome != "recovered":
        txn.status = "escalated" if action == "escalate_human" else "lost"
    else:
        txn.status = "pending"

    db.commit()
    db.refresh(attempt)
    return attempt


def run_batch(db: Session, confidence_threshold: float | None = None):
    """Runs recovery for every open (failed/pending) transaction once."""
    open_txns = db.query(Transaction).filter(Transaction.status.in_(["failed", "pending"])).all()
    results = []
    for txn in open_txns:
        results.append(process_transaction(db, txn, confidence_threshold=confidence_threshold))
    return results


def run_until_resolved(db: Session, confidence_threshold: float | None = None):
    """Runs recovery loops for every open transaction until terminal state or max attempts reached."""
    open_txns = db.query(Transaction).filter(Transaction.status.in_(["failed", "pending"])).all()
    results = []
    for txn in open_txns:
        while txn.status in ("failed", "pending"):
            attempt = process_transaction(db, txn, confidence_threshold=confidence_threshold)
            results.append(attempt)
    return results

