"""
 idempotent seed script to create a fixed canonical demo transaction
 for boringly reliable recovery simulation.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Imported 'engine' and 'Base' alongside 'SessionLocal' to handle table creation
from app.core.database import SessionLocal, engine, Base
from app.models.models import Transaction, RecoveryAttempt

def seed_demo_txn():
    db = SessionLocal()
    try:
        # 1. Clean up any existing demo state to make it idempotent
        # We find previous transactions matching our unique payment_id reference
        demo_payment_ref = "demo_pay_ref_4500"
        
        old_txns = db.query(Transaction).filter(Transaction.payment_id == demo_payment_ref).all()
        for old_txn in old_txns:
            # Delete corresponding attempts to satisfy foreign key constraint
            db.query(RecoveryAttempt).filter(RecoveryAttempt.transaction_id == old_txn.id).delete()
            db.delete(old_txn)
        
        db.commit()

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
            failure_reason="network_timeout",
            gateway="razorpay",
            bank="HDFC",
            checkout_state="failed"
        )
        
        db.add(demo_txn)
        db.commit()
        db.refresh(demo_txn)
        
        print(f"Demo transaction seeded successfully! ID={demo_txn.id}, payment_id={demo_payment_ref}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure all tables are created in the database before querying or inserting data
    Base.metadata.create_all(bind=engine)
    
    seed_demo_txn()
