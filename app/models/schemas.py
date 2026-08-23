from pydantic import BaseModel, Field
from datetime import datetime


class GenerateBatchRequest(BaseModel):
    n: int = Field(default=60, ge=1, le=500)
    seed: int | None = None
    scenario: str | None = None


class TransactionOut(BaseModel):
    id: int
    customer_id: str
    amount: float
    failure_code: str
    status: str
    attempts_count: int
    created_at: datetime
    promise_to_pay: bool
    promised_amount: float

    class Config:
        from_attributes = True


class AttemptOut(BaseModel):
    id: int
    transaction_id: int
    attempt_number: int
    diagnosis: str
    confidence: float
    action_taken: str
    reasoning: str
    cost: float
    outcome: str
    escalated: bool
    timestamp: datetime

    class Config:
        from_attributes = True
