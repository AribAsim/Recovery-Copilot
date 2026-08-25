from pydantic import BaseModel
from typing import Optional, Dict, Any
import random
from app.models.models import Transaction

# Strict Allowlist of actions permitted to pass to execution
ALLOWED_EXECUTION_ACTIONS = {
    "retry_payment",
    "retry_after_delay",
    "request_new_payment_method",
    "send_recovery_message",
    "escalate_human",
    "no_action",
    "give_up"
}

# Simulated recovery success rates for execution adapter
SIMULATED_SUCCESS_RATES: Dict[str, float] = {
    "retry_payment": 0.50,
    "retry_after_delay": 0.55,
    "request_new_payment_method": 0.65,
    "send_recovery_message": 0.35,
    "escalate_human": 0.20,
    "no_action": 0.0,
    "give_up": 0.0
}

class ExecutionResult(BaseModel):
    action_executed: str
    outcome: str  # recovered, failed, escalated, lost, skipped
    cost: float
    recovery_amount: float
    net_recovery: float
    escalated: bool

class RecoveryActionExecutor:
    """
    Execution Adapter.
    Enforces a strict boundary where only approved actions passing through the 
    Policy Decision layer are allowed to be executed.
    """
    def __init__(self, action_costs: Dict[str, float]):
        self.action_costs = action_costs

    def execute(self, approved_action: str, transaction: Transaction) -> ExecutionResult:
        # Hard check: Must be in the allowed execution action list
        if approved_action not in ALLOWED_EXECUTION_ACTIONS:
            # Panic fallback to prevent illegal actions executing
            approved_action = "escalate_human"

        cost = self.action_costs.get(approved_action, 0.0)
        escalated = approved_action in ("escalate_human", "give_up")
        
        # Outcome mapping based on deterministic/probabilistic simulator
        if approved_action == "give_up":
            outcome = "lost"
        elif approved_action == "escalate_human":
            outcome = "escalated"
        elif approved_action == "no_action":
            outcome = "skipped"
        else:
            success_p = SIMULATED_SUCCESS_RATES.get(approved_action, 0.3)
            # Roll deterministic mock probabilities using transaction id or hash as seed
            txn_seed = getattr(transaction, "id", None) or hash(transaction)
            local_rand = random.Random(txn_seed)
            outcome = "recovered" if local_rand.random() < success_p else "failed"

        recovery_amount = transaction.amount if outcome == "recovered" else 0.0
        net_recovery = recovery_amount - cost

        return ExecutionResult(
            action_executed=approved_action,
            outcome=outcome,
            cost=cost,
            recovery_amount=recovery_amount,
            net_recovery=net_recovery,
            escalated=escalated
        )
