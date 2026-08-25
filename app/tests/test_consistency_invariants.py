"""
Consistency Invariant Tests
===========================
Proves the five hard invariants of the recovery pipeline:

  1. REJECTED policy decision → execution=skipped, recovery_amount=0, net_recovery=0
  2. Executor receives exactly the policy-approved action (not the raw AI recommendation)
  3. Each RecoveryAttempt record is a self-contained snapshot (no cross-contamination)
  4. A REJECTED / skipped attempt does NOT consume an attempt counter slot
  5. The transaction's final status is determined by the latest *non-skipped* execution result
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import Transaction
from app.services.engine import process_transaction
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Pin to 02:00 — outside compliance window — and use deterministic mode."""
    settings.OPENROUTER_API_KEY = "test-key"
    settings.DIAGNOSIS_MODE = "deterministic"

    import datetime as dt

    class FrozenAt2AM:
        @classmethod
        def utcnow(cls):
            return dt.datetime(2026, 8, 26, 2, 0, 0)

        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 8, 26, 2, 0, 0)

    monkeypatch.setattr("app.services.engine.datetime", FrozenAt2AM)
    yield


def _make_infra_txn(db) -> Transaction:
    """gateway_timeout → deterministic rules recommend retry_after_delay.
    At 02:00 the compliance window hard-blocks execution."""
    txn = Transaction(
        customer_id="test-cust",
        amount=500.0,
        failure_code="gateway_timeout",
        raw_failure_text="Gateway timed out.",
    )
    db.add(txn)
    db.commit()
    return txn


# ---------------------------------------------------------------------------
# Invariant 1 — REJECTED policy → skipped execution, zero financials
# ---------------------------------------------------------------------------
def test_inv1_rejected_policy_produces_skipped_execution(db):
    txn = _make_infra_txn(db)
    attempt = process_transaction(db, txn)

    assert attempt.policy_decision == "REJECTED", (
        f"Expected REJECTED at 02:00, got {attempt.policy_decision}"
    )
    assert attempt.approved_action == "no_action", (
        f"approved_action must be 'no_action' when hard-blocked, got {attempt.approved_action}"
    )
    assert attempt.execution_result == "skipped", (
        f"execution_result must be 'skipped' when hard-blocked, got {attempt.execution_result}"
    )
    assert attempt.recovery_amount == 0, f"recovery_amount must be 0, got {attempt.recovery_amount}"
    assert attempt.net_recovery == 0, f"net_recovery must be 0, got {attempt.net_recovery}"
    assert attempt.outcome == "skipped", f"outcome must be 'skipped', got {attempt.outcome}"


# ---------------------------------------------------------------------------
# Invariant 2 — Executor receives exactly the policy-approved action
# ---------------------------------------------------------------------------
def test_inv2_executor_receives_approved_action_not_raw_recommendation(db, monkeypatch):
    """At noon the compliance window passes; the executor must act on approved_action."""
    import datetime as dt

    class NoonTime:
        @classmethod
        def utcnow(cls): return dt.datetime(2026, 8, 26, 12, 0, 0)
        @classmethod
        def now(cls, tz=None): return dt.datetime(2026, 8, 26, 12, 0, 0)

    monkeypatch.setattr("app.services.engine.datetime", NoonTime)

    txn = _make_infra_txn(db)
    attempt = process_transaction(db, txn)

    # At noon the compliance window passes, so no hard_block
    assert attempt.policy_decision == "APPROVED", (
        f"Expected APPROVED at noon, got {attempt.policy_decision}"
    )
    # The executor must have used the approved action, not raw recommendation
    assert attempt.action_taken == attempt.approved_action, (
        f"action_taken ({attempt.action_taken!r}) != approved_action ({attempt.approved_action!r})"
    )
    # And the execution must not be skipped
    assert attempt.outcome != "skipped"


# ---------------------------------------------------------------------------
# Invariant 3 — Each attempt record is self-consistent (no cross-contamination)
# ---------------------------------------------------------------------------
def test_inv3_each_attempt_record_is_self_contained(db, monkeypatch):
    """Attempt 1 blocked at 2AM; Attempt 2 approved at noon.
    After Attempt 2 runs, Attempt 1's DB record must still show 'skipped'."""
    import datetime as dt

    call_count = {"n": 0}

    class ProgressiveTime:
        @classmethod
        def utcnow(cls):
            call_count["n"] += 1
            return (dt.datetime(2026, 8, 26, 2, 0, 0)
                    if call_count["n"] <= 4
                    else dt.datetime(2026, 8, 26, 12, 0, 0))

        @classmethod
        def now(cls, tz=None):
            return cls.utcnow()

    monkeypatch.setattr("app.services.engine.datetime", ProgressiveTime)

    txn = _make_infra_txn(db)

    attempt_1 = process_transaction(db, txn)
    db.refresh(txn)
    attempt_2 = process_transaction(db, txn)
    db.refresh(attempt_1)

    # attempt_1 must still show its own data
    assert attempt_1.execution_result == "skipped", (
        "attempt_1 should still show 'skipped' after attempt_2 ran"
    )
    assert attempt_1.net_recovery == 0
    assert attempt_1.id != attempt_2.id, "Each attempt must be a distinct DB row"


# ---------------------------------------------------------------------------
# Invariant 4 — Skipped attempts do NOT consume the retry budget
# ---------------------------------------------------------------------------
def test_inv4_skipped_attempt_does_not_increment_attempt_counter(db):
    txn = _make_infra_txn(db)
    before = txn.attempts_count   # 0

    attempt = process_transaction(db, txn)
    db.refresh(txn)

    assert attempt.outcome == "skipped"
    assert txn.attempts_count == before, (
        f"attempts_count should still be {before} after a skipped attempt, got {txn.attempts_count}"
    )


# ---------------------------------------------------------------------------
# Invariant 5 — Transaction status reflects only real (non-skipped) execution
# ---------------------------------------------------------------------------

def test_inv5_txn_status_reflects_latest_non_skipped_outcome(db, monkeypatch):
    """Attempt 1 is skipped at 2AM -> txn.status must stay unchanged.
    Attempt 2 executes at noon -> txn.status reflects the real result."""
    import datetime as dt

    class At2AM:
        @classmethod
        def utcnow(cls): return dt.datetime(2026, 8, 26, 2, 0, 0)
        @classmethod
        def now(cls, tz=None): return dt.datetime(2026, 8, 26, 2, 0, 0)

    # Attempt 1 at 2AM
    monkeypatch.setattr("app.services.engine.datetime", At2AM)
    txn = _make_infra_txn(db)
    initial_status = txn.status

    attempt_1 = process_transaction(db, txn)
    db.refresh(txn)

    assert attempt_1.outcome == "skipped"
    assert txn.status == initial_status, (
        f"txn.status must remain {initial_status!r} after a skipped attempt, got {txn.status!r}"
    )

    # Attempt 2 at noon
    class AtNoon:
        @classmethod
        def utcnow(cls): return dt.datetime(2026, 8, 26, 12, 0, 0)
        @classmethod
        def now(cls, tz=None): return dt.datetime(2026, 8, 26, 12, 0, 0)

    monkeypatch.setattr("app.services.engine.datetime", AtNoon)
    attempt_2 = process_transaction(db, txn)
    db.refresh(txn)

    assert attempt_2.outcome != "skipped", "Attempt 2 at noon should not be skipped"
    valid_terminal = {"failed", "pending", "recovered", "lost", "escalated"}
    assert txn.status in valid_terminal
    if attempt_2.outcome == "recovered":
        assert txn.status == "recovered"
    elif attempt_2.outcome == "lost":
        assert txn.status in ("lost", "escalated")


