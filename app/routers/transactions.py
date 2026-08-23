from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Transaction
from app.models.schemas import GenerateBatchRequest, TransactionOut
from app.services.data_generator import generate_batch, SCENARIOS

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/generate", response_model=list[TransactionOut])
def generate(req: GenerateBatchRequest, db: Session = Depends(get_db)):
    mix = SCENARIOS.get(req.scenario) if req.scenario else None
    txns = generate_batch(db, n=req.n, mix=mix, seed=req.seed)
    return txns


@router.get("", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).all()
