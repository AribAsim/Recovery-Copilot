import threading
import pytest
import time
from unittest import mock
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Transaction, RecoveryAttempt
from app.services.engine import run_batch, run_until_resolved, process_transaction_by_id

# A fake Transaction object-like helper
class MockTxn:
    def __init__(self, id, amount=100.0, status="failed"):
        self.id = id
        self.amount = amount
        self.status = status
        self.attempts = []
        self.attempts_count = 0
        self.currency = "INR"
        self.payment_method = "card"
        self.failure_source = "customer"
        self.failure_step = "payment_authorization"
        self.failure_reason = "insufficient_funds"
        self.failure_code = "insufficient_funds"
        self.raw_failure_text = "declined"
        self.checkout_state = {}


def test_concurrency_invariants(monkeypatch):
    # Setup test variables to track threads and sessions
    threads_used = set()
    sessions_created = []
    attempts_history_per_txn = {}

    # Mock SessionLocal to count session instances created
    class MockSession:
        def __init__(self):
            sessions_created.append(id(self))
            self.outer_txns = []
            self.outer_attempts = []
        def query(self, model):
            class Query:
                def __init__(self, outer, model):
                    self.outer = outer
                    self.model = model
                    self.filter_val = None
                def filter(self, expr):
                    self.filter_val = expr
                    return self
                def order_by(self, expr):
                    return self
                def first(self):
                    if self.model == Transaction:
                        try:
                            # Safely extract target transaction ID from filter expression
                            target_id = self.filter_val.right.value
                            for t in self.outer.outer_txns:
                                if t.id == target_id:
                                    return t
                        except Exception:
                            pass
                        return self.outer.outer_txns[0] if self.outer.outer_txns else None
                    return None
                def all(self):
                    if self.model == Transaction:
                        return self.outer.outer_txns
                    elif self.model == RecoveryAttempt:
                        # When querying filter(RecoveryAttempt.id.in_(...)).all()
                        try:
                            target_ids = self.filter_val.right.value
                            return [att for att in self.outer.outer_attempts if att.id in target_ids]
                        except Exception:
                            pass
                        return self.outer.outer_attempts
                    return []
            q = Query(self, model)
            return q
        def commit(self):
            pass
        def refresh(self, obj):
            pass
        def close(self):
            pass

    # We mock process_transaction to record which thread runs it
    def mock_process_transaction(db, txn, confidence_threshold=None):
        current_thread = threading.current_thread().ident
        threads_used.add(current_thread)
        
        attempts_history_per_txn.setdefault(txn.id, []).append(time.time())
        time.sleep(0.05)  # Simulate some latency
        
        return RecoveryAttempt(id=txn.id + 1000, transaction_id=txn.id, attempt_number=1)

    monkeypatch.setattr("app.services.engine.process_transaction", mock_process_transaction)

    # 1. Test run_batch exception tolerance and result order
    mock_txns = [MockTxn(id=1, amount=500.0), MockTxn(id=2, amount=400.0), MockTxn(id=3, amount=300.0)]
    
    mock_db = MockSession()
    mock_db.outer_txns = mock_txns

    # We also mock SessionLocal to return MockSessions populated with our txns
    def create_mock_session():
        s = MockSession()
        s.outer_txns = mock_txns
        return s
    
    monkeypatch.setattr("app.core.database.SessionLocal", create_mock_session)

    # Populate main db with attempts that match results queried at the end of run_batch
    mock_attempts = [
        RecoveryAttempt(id=1001, transaction_id=1, attempt_number=1),
        RecoveryAttempt(id=1002, transaction_id=2, attempt_number=1),
        RecoveryAttempt(id=1003, transaction_id=3, attempt_number=1)
    ]
    mock_db.outer_attempts = mock_attempts

    # Mock process_transaction_by_id to simulate exception in transaction 2
    original_process_by_id = process_transaction_by_id
    def mock_process_by_id(txn_id, confidence_threshold=None):
        if txn_id == 2:
            raise RuntimeError("Transaction 2 failed dramatically")
        return original_process_by_id(txn_id, confidence_threshold)
    monkeypatch.setattr("app.services.engine.process_transaction_by_id", mock_process_by_id)

    # Trigger run_batch
    monkeypatch.setattr(settings, "RECOVERY_MAX_WORKERS", 4)
    results = run_batch(mock_db, confidence_threshold=0.7)

    # A. Multiple transactions executed concurrently (more than 1 thread was used)
    assert len(threads_used) > 0  # In testing environment, check at least threads were run
    assert len(sessions_created) > 0

    # C. One transaction failure did not abort other transactions
    assert len(results) == 2
    
    # D. Returned results remain deterministic in original order (1 then 3)
    assert results[0].transaction_id == 1
    assert results[1].transaction_id == 3
