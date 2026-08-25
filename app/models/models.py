import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    failure_code = Column(String, nullable=False)   # e.g. insufficient_funds, expired_card
    raw_failure_text = Column(String, nullable=True) # e.g. raw gateway decline texts/strings
    status = Column(String, default="failed")        # failed | recovered | lost | pending
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    attempts_count = Column(Integer, default=0)
    promise_to_pay = Column(Boolean, default=False)
    promised_amount = Column(Float, default=0.0)

    # Razorpay Canonical Fields
    payment_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    currency = Column(String, default="INR")
    payment_method = Column(String, nullable=True)  # card, upi, netbanking, wallet
    failure_source = Column(String, nullable=True)  # bank, internal, gateway, customer
    failure_step = Column(String, nullable=True)    # payment_authentication, payment_authorization
    failure_reason = Column(String, nullable=True)  # insufficient_funds, network_timeout, etc.
    gateway = Column(String, nullable=True)
    bank = Column(String, nullable=True)
    checkout_state = Column(String, nullable=True)

    attempts = relationship("RecoveryAttempt", back_populates="transaction")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, index=True)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    days_overdue = Column(Integer, default=0)
    status = Column(String, default="open")        # open | paid | escalated | written_off
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    attempts_count = Column(Integer, default=0)

    attempts = relationship("RecoveryAttempt", back_populates="invoice")


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    attempt_number = Column(Integer, nullable=False)
    diagnosis = Column(String)
    confidence = Column(Float)
    action_taken = Column(String)
    reasoning = Column(String)
    cost = Column(Float, default=0.0)
    outcome = Column(String)          # recovered | failed | escalated | skipped_low_confidence
    escalated = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # AI and Policy Gate details
    ai_recommendation = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_predicted_probability = Column(Float, nullable=True)
    ai_reasoning = Column(String, nullable=True)
    policy_decision = Column(String, nullable=True)
    policy_block_reason = Column(String, nullable=True)
    expected_recovery_value = Column(Float, nullable=True)
    actual_outcome_amount = Column(Float, default=0.0)

    # Clean structured fields
    diagnosis_source = Column(String, nullable=True)
    diagnosis_reasoning = Column(String, nullable=True)
    predictor_status = Column(String, nullable=True)
    policy_override_reason = Column(String, nullable=True)
    rules_evaluated = Column(String, nullable=True) # JSON array of checks
    approved_action = Column(String, nullable=True)
    execution_result = Column(String, nullable=True)
    recovery_amount = Column(Float, default=0.0)
    net_recovery = Column(Float, default=0.0)
    fallback_status = Column(String, nullable=True)

    transaction = relationship("Transaction", back_populates="attempts")
    invoice = relationship("Invoice", back_populates="attempts")
