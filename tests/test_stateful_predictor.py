import pytest
import os
import sys
from datetime import datetime

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.recovery_context import RecoveryContext, HistoricalAttempt
from app.services.stateful_predictor import StatefulPredictor
from app.services.recovery_value import CandidateAction

def test_probability_degradation_on_previous_failed_action():
    # Setup state context representing a transaction with a failed retry
    failed_attempt = HistoricalAttempt(
        attempt_number=1,
        action_taken="retry_payment",
        outcome="failed",
        timestamp=datetime.utcnow(),
        cost=0.0,
        recovery_amount=0.0
    )
    
    context_with_failure = RecoveryContext(
        transaction_id=1,
        amount=1000.0,
        currency="INR",
        payment_method="card",
        failure_source="customer",
        failure_step="payment_authorization",
        failure_reason="insufficient_funds",
        failure_code="insufficient_funds",
        attempt_number=2,
        attempts_history=[failed_attempt],
        actions_attempted=["retry_payment"],
        actions_failed=["retry_payment"],
        actions_succeeded=[],
        remaining_attempts=2
    )
    
    context_no_failure = RecoveryContext(
        transaction_id=2,
        amount=1000.0,
        currency="INR",
        payment_method="card",
        failure_source="customer",
        failure_step="payment_authorization",
        failure_reason="insufficient_funds",
        failure_code="insufficient_funds",
        attempt_number=1,
        attempts_history=[],
        actions_attempted=[],
        actions_failed=[],
        actions_succeeded=[],
        remaining_attempts=3
    )
    
    predictor = StatefulPredictor()
    
    candidates_no_fail = predictor.predict_candidates(None, context_no_failure)
    candidates_with_fail = predictor.predict_candidates(None, context_with_failure)
    
    prob_no_fail = next(c.probability for c in candidates_no_fail if c.action == "retry_payment")
    prob_with_fail = next(c.probability for c in candidates_with_fail if c.action == "retry_payment")
    
    # Assert that probability degradation occurs correctly
    assert prob_with_fail < prob_no_fail
    assert prob_with_fail == prob_no_fail * 0.10
    
    # Assert CandidateAction includes reason
    reason_with_fail = next(c.reason for c in candidates_with_fail if c.action == "retry_payment")
    assert "degraded" in reason_with_fail
