import pytest
import os
import sys
from datetime import datetime

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.models import Transaction, RecoveryAttempt
from app.services.policy_engine import evaluate, PolicyContext, RuleEvaluation, PolicyDecision

class MockAttempt:
    def __init__(self, action_taken, outcome):
        self.action_taken = action_taken
        self.outcome = outcome

class MockTransaction:
    def __init__(self, amount=100.0, attempts_count=0, status="failed", promise_to_pay=False, attempts=None):
        self.amount = amount
        self.attempts_count = attempts_count
        self.status = status
        self.promise_to_pay = promise_to_pay
        self.attempts = attempts or []

@pytest.fixture
def default_context():
    return PolicyContext(
        current_time=datetime(2026, 8, 25, 12, 0, 0),  # 12 PM (within operating window 8 AM - 8 PM)
        high_value_threshold=50000.0,
        confidence_threshold=0.70,
        max_retry_attempts=3
    )

def test_normal_recommendation_approved(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="failed")
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "retry_after_delay"
    assert not decision.blocked
    assert not decision.was_overridden

def test_attempts_exceeded_blocked(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=3, status="failed")
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert decision.was_overridden
    assert "max_attempts" in decision.rules_triggered

def test_immediate_retry_during_cooldown_converted(default_context):
    # If tries > 0, immediate retry (retry_payment) is blocked by cooldown and converted to retry_after_delay
    txn = MockTransaction(amount=1000.0, attempts_count=1, status="failed")
    decision = evaluate(
        recommendation="retry_payment",
        predicted_probability=0.50,
        confidence=0.90,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "retry_after_delay"
    assert decision.blocked  # Considered blocked/overridden
    assert "retry_cooldown" in decision.rules_triggered

def test_repeated_failed_action_blocked(default_context):
    # Mock prior attempts where retry_after_delay failed
    prior = [MockAttempt(action_taken="retry_after_delay", outcome="failed")]
    txn = MockTransaction(amount=1000.0, attempts_count=1, status="failed", attempts=prior)
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert "no_repeated_failed_action" in decision.rules_triggered

def test_terminal_state_blocked(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="recovered")
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "no_action"
    assert decision.blocked
    assert "transaction_eligible" in decision.rules_triggered

def test_low_confidence_escapes(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="failed")
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.50,  # Below 0.70 threshold
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert "confidence_threshold" in decision.rules_triggered

def test_malformed_recommendation(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="failed")
    decision = evaluate(
        recommendation="invalid_action_name",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert "ai_output_format" in decision.rules_triggered

def test_high_value_transaction_escalates(default_context):
    txn = MockTransaction(amount=60000.0, attempts_count=0, status="failed")  # Above 50,000 threshold
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert "high_value_limit" in decision.rules_triggered

def test_promise_to_pay_blocks(default_context):
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="failed", promise_to_pay=True)
    decision = evaluate(
        recommendation="retry_after_delay",
        predicted_probability=0.55,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"
    assert decision.blocked
    assert "promise_to_pay_inactive" in decision.rules_triggered

def test_out_of_operating_window(default_context):
    context_night = PolicyContext(
        current_time=datetime(2026, 8, 25, 23, 0, 0),  # 11 PM (operating window is 8 AM - 8 PM)
        high_value_threshold=50000.0,
        confidence_threshold=0.70,
        max_retry_attempts=3
    )
    txn = MockTransaction(amount=1000.0, attempts_count=0, status="failed")
    decision = evaluate(
        recommendation="retry_payment",
        predicted_probability=0.50,
        confidence=0.85,
        candidate_actions=[],
        transaction=txn,
        context=context_night
    )
    assert decision.approved_action == "retry_after_delay"  # Delayed scheduled action
    assert decision.blocked
    assert "compliance_operating_window" in decision.rules_triggered

def test_policy_precedence_high_value_over_high_expected_value(default_context):
    # High expected value but transaction is high value (₹60,000)
    txn = MockTransaction(amount=60000.0, attempts_count=0, status="failed")
    decision = evaluate(
        recommendation="retry_payment",
        predicted_probability=0.95,  # Generates high expected value
        confidence=0.95,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    assert decision.approved_action == "escalate_human"  # Escapes to human despite 95% recovery probability
    assert "high_value_limit" in decision.rules_triggered

def test_executor_strict_authority_boundary(default_context):
    from app.services.action_executor import RecoveryActionExecutor
    
    # 1. AI recommends "retry_payment" (immediate)
    ai_recommendation = "retry_payment"
    
    # 2. Transaction is at attempts_count=3 (Max retry limits exceeded!)
    txn = MockTransaction(amount=1000.0, attempts_count=3, status="failed")
    
    # 3. Policy evaluates the state
    decision = evaluate(
        recommendation=ai_recommendation,
        predicted_probability=0.50,
        confidence=0.90,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    
    # Policy must explicitly block the execution action, overriding it to escalate_human
    assert decision.blocked
    assert decision.approved_action == "escalate_human"
    
    # 4. Executor receives ONLY approved action
    executor = RecoveryActionExecutor(action_costs={"escalate_human": 50.0, "retry_payment": 0.0})
    exec_res = executor.execute(decision.approved_action, txn)
    
    # Executor MUST NOT execute retry_payment
    assert exec_res.action_executed == "escalate_human"
    assert exec_res.escalated
    assert exec_res.outcome == "escalated"

