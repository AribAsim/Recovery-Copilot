from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HistoricalAttempt(BaseModel):
    attempt_number: int
    action_taken: str
    outcome: str
    timestamp: datetime
    cost: float
    recovery_amount: float

class RecoveryContext(BaseModel):
    transaction_id: int
    amount: float
    currency: str
    payment_method: str
    failure_source: str
    failure_step: str
    failure_reason: str
    failure_code: str
    attempt_number: int
    checkout_state: Optional[str] = None
    
    # State history
    attempts_history: List[HistoricalAttempt]
    actions_attempted: List[str]
    actions_failed: List[str]
    actions_succeeded: List[str]
    remaining_attempts: int
    time_since_last_attempt: Optional[float] = None
