from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.models import Transaction
from app.services.data_generator import generate_batch, SCENARIOS, reset_demo_transaction
from app.services.engine import run_until_resolved
from app.routers import transactions, recovery, dashboard, invoices

Base.metadata.create_all(bind=engine)

# Auto-seed database if empty (ideal for ephemeral hackathon deployments)
db = SessionLocal()
try:
    # Check if database is empty first
    txn_count = db.query(Transaction).count()
    demo_exists = db.query(Transaction).filter(Transaction.payment_id.in_(["demo_pay_ref_4500", "demo_pay_ref_1200"])).count() == 2

    if txn_count == 0:
        print("Database is empty. Auto-seeding default demo dataset...")
        try:
            generate_batch(db, n=60, mix=SCENARIOS["baseline"], seed=42)
            run_until_resolved(db)
            print("Auto-seeding batch transactions complete.")
        except Exception as e:
            print(f"Failed to seed batch transactions: {e}")
            db.rollback()

    # Always ensure demo transactions exist (idempotent)
    if not demo_exists:
        print("Demo transactions missing. Auto-seeding demo transactions...")
        try:
            reset_demo_transaction(db)
            print("Demo transactions auto-seeded successfully.")
        except Exception as e:
            print(f"Failed to seed demo transactions: {e}")
            db.rollback()
except Exception as e:
    print(f"Auto-seeding bypassed/failed: {e}")
    db.rollback()
finally:
    db.close()



app = FastAPI(
    title="Recovery Copilot API",
    description="Bounded, auditable revenue-recovery agent for failed payments and abandoned checkouts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(recovery.router)
app.include_router(dashboard.router)
app.include_router(invoices.router)


@app.get("/health")
def health():
    return {"status": "ok"}


from fastapi.responses import HTMLResponse
import os


@app.get("/", response_class=HTMLResponse)
def root():
    # Read the index.html file from the project root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(root_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            return HTMLResponse(content=f.read(), headers=headers)
    return HTMLResponse(content="<h1>index.html not found in root directory</h1>", status_code=404)
