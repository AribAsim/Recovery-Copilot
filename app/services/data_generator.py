"""
Replay harness: generates a synthetic batch of failed transactions with
tunable failure-mix proportions. Run this with different weights to prove
the system's recovery rate isn't overfit to one lucky dataset — a direct
answer to "one cherry-picked match proves nothing."
"""

import random
from faker import Faker

from sqlalchemy.orm import Session
from app.models.models import Transaction

fake = Faker("en_IN")

DEFAULT_MIX = {
    "insufficient_funds": 0.25,
    "expired_card": 0.15,
    "network_timeout": 0.15,
    "bank_server_down": 0.10,
    "user_abandoned": 0.20,
    "invalid_cvv": 0.05,
    "card_declined_generic": 0.10,
}

SCENARIOS = {
    "baseline": DEFAULT_MIX,
    "card_heavy": {
        "insufficient_funds": 0.10, "expired_card": 0.40, "network_timeout": 0.10,
        "bank_server_down": 0.05, "user_abandoned": 0.20, "invalid_cvv": 0.10,
        "card_declined_generic": 0.05,
    },
    "infra_heavy": {
        "insufficient_funds": 0.10, "expired_card": 0.10, "network_timeout": 0.35,
        "bank_server_down": 0.25, "user_abandoned": 0.10, "invalid_cvv": 0.05,
        "card_declined_generic": 0.05,
    },
    "ambiguous_heavy": {
        "insufficient_funds": 0.10, "expired_card": 0.10, "network_timeout": 0.10,
        "bank_server_down": 0.05, "user_abandoned": 0.15, "invalid_cvv": 0.10,
        "card_declined_generic": 0.40,
    },
}



RAW_FAILURE_TEXTS = {
    "insufficient_funds": [
        "51 - Insufficient Funds",
        "NSF Decline",
        "decline: insufficient funds",
        "51 Insufficient funds / over limit",
        "Transaction declined - check account balance",
        "INSUFFICIENT_FUNDS",
        "nsf error code 51",
        "Transaction declined", # ambiguous (insufficient_funds or card_declined_generic)
        "Not enough balance to complete transaction",
        "decline 51",
        "account has insufficient funds for payment",
        "declined due to low funds"
    ],
    "expired_card": [
        "54 - Expired Card",
        "Card Expired - Contact Issuer",
        "EXPIRED_CARD",
        "decline: card has expired",
        "54 Card expired",
        "exipred card info provided",
        "Expired card (54)",
        "Invalid expiration date", # ambiguous (invalid_cvv or expired_card or card_declined_generic)
        "card status: expired",
        "cannot process: expired",
        "decline: card expired 54",
        "the card has reached its expiration date"
    ],
    "network_timeout": [
        "91 - System Error / Timeout",
        "Gateway Timeout",
        "NETWORK_TIMEOUT",
        "read timeout from upstream",
        "connection reset by peer",
        "upstream service unavailable",
        "91 Network timeout",
        "unable to process request", # ambiguous (network_timeout or bank_server_down)
        "network error connection timed out",
        "gateway response: network timeout",
        "HTTP 504 Gateway Timeout",
        "request timed out during processing"
    ],
    "bank_server_down": [
        "96 - System Malfunction",
        "Issuer Down",
        "bank server offline",
        "96 System error / bank down",
        "decline: bank unavailable",
        "BANK_DOWN",
        "Internal issuer error",
        "declined by bank", # ambiguous (bank_server_down or card_declined_generic)
        "issuer bank is not responding",
        "bank server is down/offline",
        "remote system failed to respond",
        "service disruption at issuing bank"
    ],
    "user_abandoned": [
        "User closed payment page",
        "session expired on OTP screen",
        "USER_ABANDONED",
        "canceled by customer",
        "User navigated back from checkout page",
        "customer dropped off",
        "abandoned at gateway",
        "payment failed", # ambiguous (user_abandoned or card_declined_generic)
        "user cancelled the transaction",
        "abandoned by customer during auth",
        "customer clicked cancel",
        "checkout session expired"
    ],
    "invalid_cvv": [
        "CVV Verification Failed",
        "Incorrect security code",
        "decline: invalid CVV2",
        "INVALID_CVV",
        "security code check failed",
        "CVV incorrect",
        "incorrect details", # ambiguous (invalid_cvv or expired_card)
        "card verification code incorrect",
        "decline: CVV mismatch",
        "provided card details has incorrect CVV",
        "CVC/CVV2 error"
    ],
    "card_declined_generic": [
        "05 - Do Not Honor",
        "DO_NOT_HONOR",
        "card declined by issuing bank",
        "transaction could not be processed",
        "generic decline error",
        "05 Generic decline",
        "Transaction declined", # ambiguous (card_declined_generic or insufficient_funds)
        "declined by bank", # ambiguous (card_declined_generic or bank_server_down)
        "payment failed", # ambiguous (card_declined_generic or user_abandoned)
        "declined - please contact card issuer",
        "card issuer declined this charge",
        "unable to authorize payment"
    ]
}


def generate_batch(db: Session, n: int = 60, mix: dict | None = None, seed: int | None = None):
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    mix = mix or DEFAULT_MIX
    codes = list(mix.keys())
    weights = list(mix.values())

    # Map failure codes to Razorpay failure details
    razorpay_mappings = {
        "insufficient_funds": {
            "failure_source": "customer",
            "failure_step": "payment_authorization",
            "failure_reason": "insufficient_funds",
            "payment_method": "card"
        },
        "expired_card": {
            "failure_source": "customer",
            "failure_step": "payment_authorization",
            "failure_reason": "payment_expired",
            "payment_method": "card"
        },
        "network_timeout": {
            "failure_source": "gateway",
            "failure_step": "payment_authorization",
            "failure_reason": "network_timeout",
            "payment_method": "upi"
        },
        "bank_server_down": {
            "failure_source": "bank",
            "failure_step": "payment_authorization",
            "failure_reason": "bank_server_down",
            "payment_method": "netbanking"
        },
        "user_abandoned": {
            "failure_source": "customer",
            "failure_step": "payment_authentication",
            "failure_reason": "bad_request",
            "payment_method": "upi"
        },
        "invalid_cvv": {
            "failure_source": "customer",
            "failure_step": "payment_authorization",
            "failure_reason": "bad_request",
            "payment_method": "card"
        },
        "card_declined_generic": {
            "failure_source": "gateway",
            "failure_step": "payment_authorization",
            "failure_reason": "generic_decline",
            "payment_method": "card"
        }
    }

    created = []
    for _ in range(n):
        failure_code = random.choices(codes, weights=weights, k=1)[0]
        raw_text = random.choice(RAW_FAILURE_TEXTS.get(failure_code, ["payment could not be processed"]))
        
        mapping = razorpay_mappings.get(failure_code, {
            "failure_source": "gateway",
            "failure_step": "payment_authorization",
            "failure_reason": "unknown",
            "payment_method": "card"
        })

        txn = Transaction(
            customer_id=fake.uuid4()[:8],
            amount=round(random.uniform(199, 9999), 2),
            failure_code=failure_code,
            raw_failure_text=raw_text,
            status="failed",
            attempts_count=0,
            # Canonical Fields
            payment_id=f"pay_{fake.uuid4()[:14]}",
            order_id=f"order_{fake.uuid4()[:14]}",
            currency="INR",
            payment_method=mapping["payment_method"],
            failure_source=mapping["failure_source"],
            failure_step=mapping["failure_step"],
            failure_reason=mapping["failure_reason"],
            gateway=random.choice(["razorpay", "hdfc", "sbi"]),
            bank=random.choice(["HDFC", "ICICI", "SBI", "AXIS"]),
            checkout_state=random.choice(["opened", "payment_selected", "submitted"])
        )
        db.add(txn)
        created.append(txn)

    db.commit()
    for t in created:
        db.refresh(t)
    return created


def generate_invoice_batch(db: Session, n: int = 20, seed: int | None = None):
    from app.models.models import Invoice
    from datetime import datetime, timedelta

    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    companies = [
        "Tata Consultancy Services Ltd", "Reliance Industries B2B Portal", "Infosys Technologies",
        "Wipro Enterprises", "Mahindra & Mahindra Logistics", "HDFC Corporate Banking Gateway",
        "ICICI Merchant Services", "Bharti Airtel Business Division", "Larsen & Toubro Construction",
        "Adani Ports & SEZ", "Reliance Retail Logistics", "ITC Corporate Distributors",
        "Godrej Industries Ltd", "Hindalco Industries B2B", "Bajaj Auto Distribution",
        "Grasim Industries Trade Division", "Jindal Steel & Power Ltd", "Asian Paints Corporate Sales",
        "Maruti Suzuki India Corporate Portal", "Cipla B2B Distribution"
    ]

    created = []
    for _ in range(n):
        comp = random.choice(companies)
        business_name = f"{comp} #{random.randint(100, 999)}"
        amount = round(random.uniform(5000, 150000), 2)
        days_overdue = random.randint(1, 90)
        due_date = datetime.utcnow() - timedelta(days=days_overdue)

        inv = Invoice(
            business_name=business_name,
            amount=amount,
            due_date=due_date,
            days_overdue=days_overdue,
            status="open",
            attempts_count=0
        )
        db.add(inv)
        created.append(inv)

    db.commit()
    for inv in created:
        db.refresh(inv)
    return created


def reset_demo_transaction(db: Session) -> Transaction:
    from app.models.models import Transaction, RecoveryAttempt
    
    demo_payment_ref = "demo_pay_ref_4500"
    
    try:
        # 1. Clean up any existing demo state to make it idempotent
        old_txns = db.query(Transaction).filter(Transaction.payment_id == demo_payment_ref).all()
        for old_txn in old_txns:
            # Delete corresponding attempts to satisfy foreign key constraint
            db.query(RecoveryAttempt).filter(RecoveryAttempt.transaction_id == old_txn.id).delete()
            db.delete(old_txn)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Failed to clean up old demo transaction: {e}")

    # 2. Insert fresh fixed transaction
    demo_txn = Transaction(
        customer_id="cust_demo_01",
        amount=4500.0,
        failure_code="bank_server_down",
        raw_failure_text="Bank server response timed out during authorization code lookup",
        status="failed",
        attempts_count=0,
        promise_to_pay=False,
        promised_amount=0.0,
        payment_id=demo_payment_ref,
        order_id="demo_order_101",
        currency="INR",
        payment_method="card",
        failure_source="bank",
        failure_step="payment_authorization",
        failure_reason="bank_server_down",
        gateway="razorpay",
        bank="HDFC",
        checkout_state="failed"
    )
    
    db.add(demo_txn)
    db.commit()
    db.refresh(demo_txn)
    return demo_txn
