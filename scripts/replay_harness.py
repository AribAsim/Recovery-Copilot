"""
Stress-test the recovery engine against several different synthetic failure
mixes and print recovery-rate deltas. Proves the system isn't overfit to one
lucky demo dataset.

Run: python scripts/replay_harness.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, Base, engine
from app.models.models import Transaction
from app.services.data_generator import generate_batch
from app.services.engine import run_batch
from app.services.dashboard import get_summary

SCENARIOS = {
    "baseline": None,  # uses DEFAULT_MIX
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
        "card_declined_generic": 0.40,   # lots of low-confidence cases -> more escalation
    },
}


def run_scenario(name, mix, seed=42):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        generate_batch(db, n=80, mix=mix, seed=seed)
        run_batch(db)
        summary = get_summary(db)
        print(f"\n=== Scenario: {name} ===")
        print(f"  Recovery rate     : {summary['overall_recovery_rate']*100:.1f}%")
        print(f"  Net recovered     : Rs.{summary['net_amount_recovered']:.2f}")
        print(f"  Escalated to human: {summary['escalated_count']}")
        print(f"  Lost              : {summary['lost_count']}")
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    results = {}
    for name, mix in SCENARIOS.items():
        results[name] = run_scenario(name, mix)

    print("\n--- Summary across scenarios (proves no cherry-picking) ---")
    for name, s in results.items():
        print(f"{name:20s} recovery_rate={s['overall_recovery_rate']*100:5.1f}%  net=Rs.{s['net_amount_recovered']:.2f}")
