"""
Seeding script to reset the database, generate a 60-transaction batch using 
the baseline scenario with a fixed seed, and execute run-until-resolved recovery loops.
Ensures a premium, predictable demo dataset is always ready.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, Base, engine
from app.services.data_generator import generate_batch, SCENARIOS
from app.services.engine import run_until_resolved

def seed_demo():
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Generating 60 transactions using baseline scenario (seed=42)...")
        # baseline scenario resolves to DEFAULT_MIX failure proportions
        generate_batch(db, n=60, mix=SCENARIOS["baseline"], seed=42)
        
        print("Running run-until-resolved over all generated transactions...")
        attempts = run_until_resolved(db)
        print(f"Processed {len(attempts)} attempts successfully.")
        
        print("Seeding complete! Known-good demonstration dataset is ready.")
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo()
