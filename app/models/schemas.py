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
    payment_id: str | None = None

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    business_name: str
    amount: float
    due_date: datetime
    days_overdue: int
    status: str
    attempts_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AttemptOut(BaseModel):
    id: int
    transaction_id: int | None = None
    invoice_id: int | None = None
    attempt_number: int
    diagnosis: str
    confidence: float
    action_taken: str
    reasoning: str
    cost: float
    outcome: str
    escalated: bool
    timestamp: datetime

    # New fields
    ai_recommendation: str | None = None
    ai_confidence: float | None = None
    ai_predicted_probability: float | None = None
    ai_reasoning: str | None = None
    policy_decision: str | None = None
    policy_block_reason: str | None = None
    expected_recovery_value: float | None = None
    actual_outcome_amount: float | None = None

    diagnosis_source: str | None = None
    diagnosis_reasoning: str | None = None
    predictor_status: str | None = None
    policy_override_reason: str | None = None
    rules_evaluated: str | None = None # JSON string
    approved_action: str | None = None
    execution_result: str | None = None
    recovery_amount: float | None = None
    net_recovery: float | None = None
    fallback_status: str | None = None

    class Config:
        from_attributes = True
