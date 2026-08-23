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



def generate_batch(db: Session, n: int = 60, mix: dict | None = None, seed: int | None = None):
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    mix = mix or DEFAULT_MIX
    codes = list(mix.keys())
    weights = list(mix.values())

    created = []
    for _ in range(n):
        failure_code = random.choices(codes, weights=weights, k=1)[0]
        txn = Transaction(
            customer_id=fake.uuid4()[:8],
            amount=round(random.uniform(199, 9999), 2),
            failure_code=failure_code,
            status="failed",
            attempts_count=0,
        )
        db.add(txn)
        created.append(txn)

    db.commit()
    for t in created:
        db.refresh(t)
    return created
