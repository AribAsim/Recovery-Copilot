"""
 idempotent seed script to create a fixed canonical demo transaction
 for boringly reliable recovery simulation.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.services.data_generator import reset_demo_transaction

def seed_demo_txn():
    db = SessionLocal()
    try:
        reset_demo_transaction(db)
        print("Demo transaction seeded successfully! payment_id=demo_pay_ref_4500")
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure all tables are created in the database before querying or inserting data
    Base.metadata.create_all(bind=engine)
    
    seed_demo_txn()

