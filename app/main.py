from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.models import Transaction
from app.services.data_generator import generate_batch, SCENARIOS
from app.services.engine import run_until_resolved
from app.routers import transactions, recovery, dashboard, invoices

Base.metadata.create_all(bind=engine)

# Auto-seed database if empty (ideal for ephemeral hackathon deployments)
db = SessionLocal()
try:
    if db.query(Transaction).count() == 0:
        print("Database is empty. Auto-seeding default demo dataset...")
        generate_batch(db, n=60, mix=SCENARIOS["baseline"], seed=42)
        run_until_resolved(db)
        print("Auto-seeding complete.")
except Exception as e:
    print(f"Auto-seeding bypassed/failed: {e}")
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
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>index.html not found in root directory</h1>", status_code=404)

