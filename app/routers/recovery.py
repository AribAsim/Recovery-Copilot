from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Transaction, RecoveryAttempt
from app.models.schemas import AttemptOut
from app.services.engine import process_transaction, run_batch, run_until_resolved
router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.get("/settings")
def get_recovery_settings():
    return {
        "DIAGNOSIS_MODE": settings.DIAGNOSIS_MODE,
        "CONFIDENCE_THRESHOLD": settings.CONFIDENCE_THRESHOLD,
    }


@router.post("/settings")
def update_recovery_settings(payload: dict):
    if "DIAGNOSIS_MODE" in payload:
        mode = payload["DIAGNOSIS_MODE"]
        if mode in ("llm", "deterministic"):
            settings.DIAGNOSIS_MODE = mode
    if "CONFIDENCE_THRESHOLD" in payload:
        try:
            settings.CONFIDENCE_THRESHOLD = float(payload["CONFIDENCE_THRESHOLD"])
        except (ValueError, TypeError):
            pass
    return {
        "DIAGNOSIS_MODE": settings.DIAGNOSIS_MODE,
        "CONFIDENCE_THRESHOLD": settings.CONFIDENCE_THRESHOLD,
    }


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


@router.get("/outcome-dataset")
def get_outcome_dataset_endpoint(db: Session = Depends(get_db)):
    """Export the audited outcome intelligence dataset as a CSV stream."""
    from fastapi.responses import StreamingResponse
    from app.services.outcome_recorder import export_outcome_intelligence_csv
    
    csv_data = export_outcome_intelligence_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outcome_intelligence_dataset.csv"}
    )
