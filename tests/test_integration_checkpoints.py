import pytest
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.models import Transaction, RecoveryAttempt
from app.services.policy_engine import evaluate, PolicyContext
from app.services.action_executor import RecoveryActionExecutor

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
        current_time=datetime(2026, 8, 25, 12, 0, 0),
        high_value_threshold=50000.0,
        confidence_threshold=0.70,
        max_retry_attempts=3
    )

def test_scenario_a_ai_approved(default_context):
    """
    Scenario A: AI recommends 'retry_after_delay'. Policy approves it.
    Executor runs retry_after_delay.
    """
    txn = MockTransaction(amount=100.0, attempts_count=0, status="failed")
    
    # 1. AI predicts
    ai_rec = "retry_after_delay"
    confidence = 0.90
    prob = 0.55
    
    # 2. Policy evaluates
    decision = evaluate(
        recommendation=ai_rec,
        predicted_probability=prob,
        confidence=confidence,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    
    assert decision.approved_action == "retry_after_delay"
    assert not decision.blocked
    
    # 3. Executor runs only approved action
    executor = RecoveryActionExecutor(action_costs={"retry_after_delay": 0.0})
    result = executor.execute(decision.approved_action, txn)
    
    assert result.action_executed == "retry_after_delay"
    assert result.outcome in ("recovered", "failed")

def test_scenario_b_ai_overridden(default_context):
    """
    Scenario B: AI recommends 'retry_payment' (immediate) on attempt 2.
    Policy blocks immediate retry due to cooldown rules and overrides it to 'retry_after_delay'.
    Executor executes only 'retry_after_delay'.
    """
    txn = MockTransaction(amount=100.0, attempts_count=1, status="failed") # attempt_number = 2
    
    # 1. AI predicts immediate retry
    ai_rec = "retry_payment"
    confidence = 0.90
    prob = 0.50
    
    # 2. Policy evaluates
    decision = evaluate(
        recommendation=ai_rec,
        predicted_probability=prob,
        confidence=confidence,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    
    assert decision.blocked
    assert decision.approved_action == "retry_after_delay" # Cooldown rule overrides
    
    # 3. Executor executes the override approved action
    executor = RecoveryActionExecutor(action_costs={"retry_after_delay": 0.0, "retry_payment": 0.0})
    result = executor.execute(decision.approved_action, txn)
    
    assert result.action_executed == "retry_after_delay"
    assert result.outcome in ("recovered", "failed")

def test_scenario_c_ai_unavailable(default_context):
    """
    Scenario C: AI is unavailable (malformed output structure/unknown action recommendation).
    Policy blocks/rejects the prediction and reverts the flow to 'escalate_human' fallback.
    Executor executes ONLY 'escalate_human'.
    """
    txn = MockTransaction(amount=100.0, attempts_count=0, status="failed")
    
    # 1. AI yields malformed/null output due to exception
    ai_rec = None
    confidence = None
    prob = None
    
    # 2. Policy evaluates
    decision = evaluate(
        recommendation=ai_rec,
        predicted_probability=prob,
        confidence=confidence,
        candidate_actions=[],
        transaction=txn,
        context=default_context
    )
    
    assert decision.blocked
    assert decision.approved_action == "escalate_human" # Strict deterministic safe routing
    
    # 3. Executor executes ONLY the fallback action
    executor = RecoveryActionExecutor(action_costs={"escalate_human": 50.0})
    result = executor.execute(decision.approved_action, txn)
    
    assert result.action_executed == "escalate_human"
    assert result.escalated
    assert result.outcome == "escalated"
