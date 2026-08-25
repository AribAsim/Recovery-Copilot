import csv
import json
import io
from typing import List
from sqlalchemy.orm import Session
from app.models.models import RecoveryAttempt

def export_outcome_intelligence_csv(db: Session) -> str:
    """
    Query all RecoveryAttempt records and construct a structured CSV dataset.
    This serves as the Outcome Intelligence dataset for offline model evaluation,
    audits, and future batch training.
    """
    attempts = db.query(RecoveryAttempt).order_by(RecoveryAttempt.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Define canonical column headers spanning transaction, AI, policy, execution, and outcomes
    headers = [
        "attempt_id",
        "timestamp",
        # Transaction Features
        "transaction_id",
        "amount",
        "payment_method",
        "gateway",
        "bank",
        # Failure characteristics
        "failure_code",
        "failure_source",
        "failure_step",
        "failure_reason",
        # AI Predictor Output
        "ai_recommendation",
        "ai_confidence",
        "ai_predicted_probability",
        "ai_reasoning",
        "predictor_status",
        # Policy Evaluation details
        "policy_decision",
        "policy_block_reason",
        "policy_override_reason",
        "rules_evaluated",
        # Execution Outcomes
        "action_executed",
        "execution_result",
        "cost",
        "recovery_amount",
        "net_recovery",
        "fallback_status"
    ]
    writer.writerow(headers)
    
    for attempt in attempts:
        txn = attempt.transaction
        
        # If attempt has no transaction (B2B invoice path), retrieve fallback empty attributes
        txn_id = txn.id if txn else ""
        amount = txn.amount if txn else ""
        payment_method = txn.payment_method if txn else ""
        gateway = txn.gateway if txn else ""
        bank = txn.bank if txn else ""
        failure_code = txn.failure_code if txn else ""
        failure_source = txn.failure_source if txn else ""
        failure_step = txn.failure_step if txn else ""
        failure_reason = txn.failure_reason if txn else ""

        writer.writerow([
            attempt.id,
            attempt.timestamp.isoformat() if attempt.timestamp else "",
            txn_id,
            amount,
            payment_method,
            gateway,
            bank,
            failure_code,
            failure_source,
            failure_step,
            failure_reason,
            attempt.ai_recommendation,
            attempt.ai_confidence,
            attempt.ai_predicted_probability,
            attempt.ai_reasoning,
            attempt.predictor_status,
            attempt.policy_decision,
            attempt.policy_block_reason,
            attempt.policy_override_reason,
            attempt.rules_evaluated,
            attempt.action_taken,
            attempt.outcome,
            attempt.cost,
            attempt.actual_outcome_amount,
            attempt.net_recovery,
            attempt.fallback_status
        ])
        
    return output.getvalue()
