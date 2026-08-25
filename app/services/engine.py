import random
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Transaction, Invoice, RecoveryAttempt
from app.services.classifier import classify_failure
from app.services import llm_classifier
from app.services.decision_router import decide_action, decide_b2b_action
from app.services.llm_client import generate_message
from app.services.recovery_value import compute_expected_value, CandidateAction

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
    import json
    from datetime import datetime
    from app.services.policy_engine import evaluate as evaluate_policy, PolicyContext

    # Construct Policy Context
    context = PolicyContext(
        current_time=datetime.utcnow(),
        high_value_threshold=getattr(settings, "HIGH_VALUE_THRESHOLD", 50000.0),
        confidence_threshold=confidence_threshold if confidence_threshold is not None else settings.CONFIDENCE_THRESHOLD,
        max_retry_attempts=settings.MAX_RETRY_ATTEMPTS
    )

    # --- Diagnose ---
    mode = getattr(settings, "DIAGNOSIS_MODE", "llm")
    if mode == "llm":
        diag = llm_classifier.classify(txn.raw_failure_text, txn.failure_code)
        predictor_status = diag.get("predictor_status", "success")
        fallback_status = diag.get("fallback_status", "Inactive")
        if predictor_status == "fallback":
            diag_source = "Deterministic Rules"
        else:
            diag_source = "AI"
    else:
        diag_val = classify_failure(txn.failure_code)
        diag = {
            "diagnosis": diag_val["diagnosis"],
            "confidence": diag_val["confidence"],
            "reasoning": "Deterministic fallback diagnosis used.",
            "raw_reasoning": "Rules engine used."
        }
        diag_source = "Deterministic Rules"
        predictor_status = "fallback"
        fallback_status = "Active"

    # Build Recovery Context
    from app.services.recovery_context import RecoveryContext, HistoricalAttempt
    from app.services.stateful_predictor import StatefulPredictor
    
    attempts_history = []
    actions_attempted = []
    actions_failed = []
    actions_succeeded = []
    last_timestamp = None
    
    for att in txn.attempts:
        attempts_history.append(
            HistoricalAttempt(
                attempt_number=att.attempt_number,
                action_taken=att.action_taken,
                outcome=att.outcome,
                timestamp=att.timestamp,
                cost=att.cost or 0.0,
                recovery_amount=att.actual_outcome_amount or 0.0
            )
        )
        actions_attempted.append(att.action_taken)
        if att.outcome == "failed":
            actions_failed.append(att.action_taken)
        elif att.outcome == "recovered":
            actions_succeeded.append(att.action_taken)
        last_timestamp = att.timestamp
        
    time_since = None
    if last_timestamp:
        time_since = (datetime.utcnow() - last_timestamp).total_seconds()
        
    rec_context = RecoveryContext(
        transaction_id=txn.id,
        amount=txn.amount,
        currency=txn.currency or "INR",
        payment_method=txn.payment_method or "card",
        failure_source=txn.failure_source or "customer",
        failure_step=txn.failure_step or "payment_authorization",
        failure_reason=txn.failure_reason or "insufficient_funds",
        failure_code=txn.failure_code or "insufficient_funds",
        attempt_number=txn.attempts_count + 1,
        checkout_state=txn.checkout_state,
        attempts_history=attempts_history,
        actions_attempted=actions_attempted,
        actions_failed=actions_failed,
        actions_succeeded=actions_succeeded,
        remaining_attempts=max(0, context.max_retry_attempts - txn.attempts_count),
        time_since_last_attempt=time_since
    )

    # --- Predict candidate actions / expected values ---
    predictor = StatefulPredictor()
    candidates = predictor.predict_candidates(txn, rec_context)
    
    # Expected net value calculations
    valued_actions = compute_expected_value(txn.amount, candidates, settings.ACTION_COST)
    
    # We rank candidates by EV descending and select the top action as our target recommendation
    best_candidate = valued_actions[0] if valued_actions else None
    recommendation = best_candidate.action if best_candidate else "escalate_human"
    selected_ev = best_candidate.expected_value if best_candidate else 0.0
    predicted_prob = best_candidate.probability if best_candidate else 0.0
    ai_conf_score = next((c.confidence for c in candidates if c.action == recommendation), 0.95)

    from app.services.action_executor import RecoveryActionExecutor

    # --- POLICY ENGINE GATE ---
    policy_dec = evaluate_policy(
        recommendation=recommendation,
        predicted_probability=predicted_prob,
        confidence=diag["confidence"],
        candidate_actions=candidates,
        transaction=txn,
        context=context
    )

    # --- Controlled Executor performs only approved actions ---
    executor = RecoveryActionExecutor(action_costs=settings.ACTION_COST)
    exec_res = executor.execute(policy_dec.approved_action, txn)

    action = exec_res.action_executed
    cost = exec_res.cost
    outcome = exec_res.outcome
    recovery_amount = exec_res.recovery_amount
    net_recovery = exec_res.net_recovery
    escalated = exec_res.escalated

    message = generate_message(action, txn.amount) if action in (
        "send_recovery_message", "request_new_payment_method"
    ) else None

    # Serializing rules evaluated
    rules_eval_serialized = json.dumps([
        {"rule": r.rule, "passed": r.passed, "detail": r.detail}
        for r in policy_dec.rules_evaluated
    ])

    # --- Persist audit trail ---
    attempt = RecoveryAttempt(
        transaction_id=txn.id,
        attempt_number=txn.attempts_count + 1,
        diagnosis=diag["diagnosis"],
        confidence=diag["confidence"],
        action_taken=action,
        reasoning=diag["reasoning"],
        cost=cost,
        outcome=outcome,
        escalated=escalated,

        # New fields
        ai_recommendation=recommendation,
        ai_confidence=ai_conf_score if diag_source == "AI" else None,
        ai_predicted_probability=predicted_prob,
        ai_reasoning=next((c.reason for c in candidates if c.action == recommendation), diag["reasoning"]),
        policy_decision="REJECTED" if policy_dec.blocked else "APPROVED",
        policy_block_reason=policy_dec.override_reason,
        expected_recovery_value=selected_ev,
        actual_outcome_amount=recovery_amount,
        
        diagnosis_source=diag_source,
        diagnosis_reasoning=diag["reasoning"],
        predictor_status=predictor_status,
        policy_override_reason=policy_dec.override_reason if policy_dec.was_overridden else None,
        rules_evaluated=rules_eval_serialized,
        approved_action=action,
        execution_result=outcome,
        recovery_amount=recovery_amount,
        net_recovery=net_recovery,
        fallback_status=fallback_status
    )
    db.add(attempt)

    txn.attempts_count += 1
    if outcome == "recovered":
        txn.status = "recovered"
        if action == "send_recovery_message":
            txn.promise_to_pay = True
            txn.promised_amount = txn.amount
    elif txn.attempts_count >= settings.MAX_RETRY_ATTEMPTS or outcome == "lost":
        txn.status = "escalated" if action == "escalate_human" else "lost"
    else:
        txn.status = "pending"

    db.commit()
    db.refresh(attempt)
    return attempt


def process_transaction_by_id(txn_id: int, confidence_threshold: float | None = None) -> int:
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if not txn:
            raise ValueError(f"Transaction {txn_id} not found")
        attempt = process_transaction(db, txn, confidence_threshold=confidence_threshold)
        return attempt.id
    finally:
        db.close()


def process_transaction_until_resolved(txn_id: int, confidence_threshold: float | None = None) -> list[int]:
    from app.core.database import SessionLocal
    db = SessionLocal()
    attempt_ids = []
    try:
        while True:
            txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
            if not txn or txn.status not in ("failed", "pending"):
                break
            attempt = process_transaction(db, txn, confidence_threshold=confidence_threshold)
            attempt_ids.append(attempt.id)
            db.refresh(txn)
        return attempt_ids
    finally:
        db.close()


def run_batch(db: Session, confidence_threshold: float | None = None):
    """Runs recovery for every open (failed/pending) transaction once."""
    open_txns = db.query(Transaction).filter(Transaction.status.in_(["failed", "pending"])).order_by(Transaction.amount.desc()).all()
    txn_ids = [txn.id for txn in open_txns]
    
    results = []
    if not txn_ids:
        return results

    tid_to_attempt_id = {}
    with ThreadPoolExecutor(max_workers=settings.RECOVERY_MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_transaction_by_id, tid, confidence_threshold): tid
            for tid in txn_ids
        }
        for future in futures:
            tid = futures[future]
            try:
                aid = future.result()
                tid_to_attempt_id[tid] = aid
            except Exception as e:
                import sys
                print(f"Error processing transaction ID {tid}: {e}", file=sys.stderr)

    attempt_ids = []
    for tid in txn_ids:
        if tid in tid_to_attempt_id:
            attempt_ids.append(tid_to_attempt_id[tid])

    if attempt_ids:
        db.commit()
        db_attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.id.in_(attempt_ids)).all()
        id_to_attempt = {att.id: att for att in db_attempts}
        for aid in attempt_ids:
            if aid in id_to_attempt:
                results.append(id_to_attempt[aid])

    return results


def run_until_resolved(db: Session, confidence_threshold: float | None = None):
    """Runs recovery loops for every open transaction until terminal state or max attempts reached."""
    open_txns = db.query(Transaction).filter(Transaction.status.in_(["failed", "pending"])).order_by(Transaction.amount.desc()).all()
    txn_ids = [txn.id for txn in open_txns]

    results = []
    if not txn_ids:
        return results

    tid_to_attempt_ids = {}
    with ThreadPoolExecutor(max_workers=settings.RECOVERY_MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_transaction_until_resolved, tid, confidence_threshold): tid
            for tid in txn_ids
        }
        for future in futures:
            tid = futures[future]
            try:
                aids = future.result()
                tid_to_attempt_ids[tid] = aids
            except Exception as e:
                import sys
                print(f"Error processing transaction ID {tid} until resolved: {e}", file=sys.stderr)

    flat_attempt_ids = []
    for tid in txn_ids:
        if tid in tid_to_attempt_ids:
            flat_attempt_ids.extend(tid_to_attempt_ids[tid])

    if flat_attempt_ids:
        db.commit()
        db_attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.id.in_(flat_attempt_ids)).all()
        id_to_attempt = {att.id: att for att in db_attempts}
        for aid in flat_attempt_ids:
            if aid in id_to_attempt:
                results.append(id_to_attempt[aid])

    return results


# Actions that plausibly "succeed" in B2B invoice collection simulation
B2B_SUCCESS_RATE = {
    "send_reminder": 0.25,
    "send_formal_notice": 0.40,
    "escalate_human": 0.15,
    "escalate_legal_review": 0.05,
}


def process_invoice(db: Session, invoice: Invoice) -> RecoveryAttempt:
    """Runs ONE recovery attempt for a B2B invoice and persists the audit trail."""

    # --- Stopping rule guard ---
    if invoice.attempts_count >= settings.MAX_RETRY_ATTEMPTS:
        invoice.status = "written_off"
        db.commit()
        attempt = RecoveryAttempt(
            invoice_id=invoice.id,
            attempt_number=invoice.attempts_count + 1,
            diagnosis="stopping_rule_triggered",
            confidence=1.0,
            action_taken="give_up",
            reasoning=f"Max attempts ({settings.MAX_RETRY_ATTEMPTS}) reached — invoice marked as written_off.",
            cost=0.0,
            outcome="written_off",
            escalated=False,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return attempt

    # --- Diagnose ---
    diag = {
        "diagnosis": f"overdue_{invoice.days_overdue}_days",
        "confidence": 1.0,
        "reasoning": f"B2B invoice is {invoice.days_overdue} days overdue."
    }

    # --- Decide ---
    action, reasoning = decide_b2b_action(invoice.days_overdue)

    # --- Self-check ---
    prior_actions = {a.action_taken for a in invoice.attempts}
    if action in prior_actions and action not in ("escalate_human", "escalate_legal_review", "give_up"):
        action = "escalate_human"
        reasoning += " | Self-check: this action already failed before, escalating to human instead."

    # --- Execute (simulated) ---
    cost = settings.ACTION_COST.get(action, 0.0)
    escalated = action in ("escalate_human", "escalate_legal_review")

    if escalated:
        outcome = "escalated"
    else:
        success_p = B2B_SUCCESS_RATE.get(action, 0.2)
        outcome = "recovered" if random.random() < success_p else "failed"

    # --- Persist audit trail ---
    attempt = RecoveryAttempt(
        invoice_id=invoice.id,
        attempt_number=invoice.attempts_count + 1,
        diagnosis=diag["diagnosis"],
        confidence=diag["confidence"],
        action_taken=action,
        reasoning=f"{reasoning} [mode=deterministic]",
        cost=cost,
        outcome=outcome,
        escalated=escalated,
    )
    db.add(attempt)

    invoice.attempts_count += 1
    if outcome == "recovered":
        invoice.status = "paid"
    elif outcome == "escalated":
        invoice.status = "escalated"
    elif invoice.attempts_count >= settings.MAX_RETRY_ATTEMPTS:
        invoice.status = "written_off"
    else:
        invoice.status = "open"

    db.commit()
    db.refresh(attempt)
    return attempt


def run_invoice_batch(db: Session):
    """Runs recovery for every open B2B invoice once."""
    open_invoices = db.query(Invoice).filter(Invoice.status == "open").order_by(Invoice.days_overdue.desc()).all()
    results = []
    for inv in open_invoices:
        results.append(process_invoice(db, inv))
    return results


def run_invoices_until_resolved(db: Session):
    """Runs recovery loops for every open B2B invoice until terminal state or max attempts reached."""
    open_invoices = db.query(Invoice).filter(Invoice.status == "open").order_by(Invoice.days_overdue.desc()).all()
    results = []
    for inv in open_invoices:
        while inv.status == "open":
            attempt = process_invoice(db, inv)
            results.append(attempt)
    return results

