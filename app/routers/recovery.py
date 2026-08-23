from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Transaction, RecoveryAttempt
from app.models.schemas import AttemptOut
from app.services.engine import process_transaction, run_batch, run_until_resolved

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/run-batch", response_model=list[AttemptOut])
def run_batch_endpoint(confidence_threshold: float | None = None, db: Session = Depends(get_db)):
    """Runs one recovery pass over every open transaction."""
    return run_batch(db, confidence_threshold=confidence_threshold)


@router.post("/run-until-resolved", response_model=list[AttemptOut])
def run_until_resolved_endpoint(confidence_threshold: float | None = None, db: Session = Depends(get_db)):
    """Runs recovery loops per open transaction until it reaches a terminal status."""
    return run_until_resolved(db, confidence_threshold=confidence_threshold)


@router.post("/run/{transaction_id}", response_model=AttemptOut)
def run_single(transaction_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return process_transaction(db, txn)


@router.get("/audit/{transaction_id}", response_model=list[AttemptOut])
def get_audit_trail(transaction_id: int, db: Session = Depends(get_db)):
    """Full explainable audit trail for one transaction — this is the 'show your work' proof."""
    return (
        db.query(RecoveryAttempt)
        .filter(RecoveryAttempt.transaction_id == transaction_id)
        .order_by(RecoveryAttempt.attempt_number)
        .all()
    )
