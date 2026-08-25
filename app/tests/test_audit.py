import pytest
import httpx
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import Transaction, RecoveryAttempt
from app.services.engine import process_transaction
from app.services import llm_classifier
from app.core.config import settings

# In-memory SQLite for isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    old_key = settings.OPENROUTER_API_KEY
    settings.OPENROUTER_API_KEY = "test-mock-key"
    settings.DIAGNOSIS_MODE = "llm"

    # Mock datetime to ensure it falls within the compliance operating window (8 AM to 8 PM)
    import datetime as dt
    class MockDatetime:
        @classmethod
        def utcnow(cls):
            return dt.datetime(2026, 8, 26, 12, 0, 0)

        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 8, 26, 12, 0, 0)

    monkeypatch.setattr("app.services.engine.datetime", MockDatetime)
    yield
    settings.OPENROUTER_API_KEY = old_key



def test_1_valid_ai_response(db_session, monkeypatch):
    # Mocking standard valid OpenRouter response
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "category": "insufficient_funds",
                            "confidence": 0.95,
                            "reasoning": "The user has insufficient funds."
                        })
                    }
                }]
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: MockResponse())

    txn = Transaction(customer_id="cust-1", amount=100.0, failure_code="insufficient_funds", raw_failure_text="Declined: Insufficient funds in card.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "insufficient_funds"
    assert attempt.confidence == 0.95
    assert attempt.diagnosis_source == "AI"
    assert attempt.predictor_status == "success"
    assert attempt.fallback_status == "Inactive"
    # Ensure no internal keys or error strings in the public reasoning field
    assert "LLM fallback" not in attempt.reasoning
    assert "Error:" not in attempt.reasoning
    assert attempt.policy_decision == "APPROVED"
    
    rules = json.loads(attempt.rules_evaluated)
    assert len(rules) > 0
    assert any(r["rule"] == "transaction_eligible" and r["passed"] for r in rules)


def test_2_ai_returns_content_none(db_session, monkeypatch):
    # AI response message has content = None
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "refusal": "Refused due to policy"
                    }
                }]
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: MockResponse())

    txn = Transaction(customer_id="cust-2", amount=150.0, failure_code="expired_card", raw_failure_text="Card has expired.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    # Recovery pipeline must continue and deterministic fallback must trigger
    assert attempt.diagnosis == "expired_card" # fallback diagnosis
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert attempt.fallback_status == "Active"
    assert "Error" not in attempt.diagnosis_reasoning
    assert "refusal" not in attempt.diagnosis_reasoning
    assert "content" not in attempt.diagnosis_reasoning


def test_3_ai_returns_malformed_json(db_session, monkeypatch):
    # Content is not valid JSON
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Not a JSON block! {category: invalid}"
                    }
                }]
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: MockResponse())

    txn = Transaction(customer_id="cust-3", amount=200.0, failure_code="invalid_cvv", raw_failure_text="CVV invalid.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "invalid_cvv"
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert attempt.fallback_status == "Active"
    assert "Not a JSON block" not in attempt.diagnosis_reasoning


def test_4_ai_timeout(db_session, monkeypatch):
    # Post raises a TimeoutException
    def mock_post_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Connection timed out")

    monkeypatch.setattr(httpx, "post", mock_post_timeout)

    txn = Transaction(customer_id="cust-4", amount=250.0, failure_code="network_timeout", raw_failure_text="Connection error.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "network_timeout"
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert attempt.fallback_status == "Active"
    assert "Connection timed out" not in attempt.diagnosis_reasoning


def test_5_ai_refusal(db_session, monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "refusal": "I cannot complete this request."
                    }
                }]
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: MockResponse())

    txn = Transaction(customer_id="cust-5", amount=300.0, failure_code="user_abandoned", raw_failure_text="User closed checkout.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "user_abandoned"
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert "refusal" not in attempt.diagnosis_reasoning


def test_6_ai_unavailable(db_session, monkeypatch):
    # Mocking HTTP Status Error (503 Service Unavailable)
    def mock_post_unavailable(*args, **kwargs):
        req = httpx.Request("POST", "https://openrouter.ai")
        resp = httpx.Response(503, request=req, content=b"Service Unavailable")
        raise httpx.HTTPStatusError("503 Service Unavailable", request=req, response=resp)

    monkeypatch.setattr(httpx, "post", mock_post_unavailable)

    txn = Transaction(customer_id="cust-6", amount=350.0, failure_code="bank_server_down", raw_failure_text="Bank server failed to respond.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "bank_server_down"
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert "503" not in attempt.diagnosis_reasoning


def test_7_deterministic_fallback(db_session):
    # Ensure policy engine receives valid input and executes cleanly even in fallback
    settings.DIAGNOSIS_MODE = "deterministic"
    
    txn = Transaction(customer_id="cust-7", amount=500.0, failure_code="insufficient_funds", raw_failure_text="Insufficient balance.")
    db_session.add(txn)
    db_session.commit()

    attempt = process_transaction(db_session, txn)

    assert attempt.diagnosis == "insufficient_funds"
    assert attempt.diagnosis_source == "Deterministic Rules"
    assert attempt.predictor_status == "fallback"
    assert attempt.fallback_status == "Active"
    assert attempt.policy_decision == "APPROVED"
    assert attempt.action_taken == "request_new_payment_method"
