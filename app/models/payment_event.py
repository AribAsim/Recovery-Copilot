from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class PaymentEvent(BaseModel):
    payment_id: str
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    payment_method: str  # card, upi, netbanking, wallet, etc.
    payment_status: str  # failed, authorized, captured, etc.
    event_type: str = "payment.failed"
    failure_code: str  # e.g., bad_request, gate_error, generic_decline
    failure_description: Optional[str] = None
    failure_source: str  # e.g., bank, internal, gateway, customer
    failure_step: str  # e.g., payment_authentication, payment_authorization
    failure_reason: str  # e.g., insufficient_funds, payment_expired, network_timeout, bad_request
    gateway: Optional[str] = None
    bank: Optional[str] = None
    attempt_number: int = 1
    checkout_state: Optional[str] = None
    customer_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
