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
    status = Column(String, default="failed")        # failed | recovered | lost | pending
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    attempts_count = Column(Integer, default=0)
    promise_to_pay = Column(Boolean, default=False)
    promised_amount = Column(Float, default=0.0)

    attempts = relationship("RecoveryAttempt", back_populates="transaction")


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    attempt_number = Column(Integer, nullable=False)
    diagnosis = Column(String)
    confidence = Column(Float)
    action_taken = Column(String)
    reasoning = Column(String)
    cost = Column(Float, default=0.0)
    outcome = Column(String)          # recovered | failed | escalated | skipped_low_confidence
    escalated = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    transaction = relationship("Transaction", back_populates="attempts")
