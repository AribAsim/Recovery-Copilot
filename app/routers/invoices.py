from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.models import Invoice, RecoveryAttempt
from app.models.schemas import InvoiceOut, AttemptOut, GenerateBatchRequest
from app.services.data_generator import generate_invoice_batch
from app.services.engine import process_invoice, run_invoice_batch, run_invoices_until_resolved

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    """List all B2B invoices."""
    return db.query(Invoice).order_by(Invoice.days_overdue.desc()).all()


@router.post("/generate", response_model=list[InvoiceOut])
def generate_invoices_endpoint(req: GenerateBatchRequest, db: Session = Depends(get_db)):
    """Generates a batch of synthetic B2B invoices."""
    return generate_invoice_batch(db, n=req.n, seed=req.seed)


@router.post("/run-batch", response_model=list[AttemptOut])
def run_invoice_batch_endpoint(db: Session = Depends(get_db)):
    """Runs one escalation pass over every open B2B invoice."""
    return run_invoice_batch(db)


@router.post("/run-until-resolved", response_model=list[AttemptOut])
def run_invoices_until_resolved_endpoint(db: Session = Depends(get_db)):
    """Runs escalation loops per open B2B invoice until it reaches a terminal status."""
    return run_invoices_until_resolved(db)


@router.post("/run/{invoice_id}", response_model=AttemptOut)
def run_single_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Run one escalation action for a single B2B invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return process_invoice(db, invoice)


@router.get("/audit/{invoice_id}", response_model=list[AttemptOut])
def get_invoice_audit_trail(invoice_id: int, db: Session = Depends(get_db)):
    """Explainable audit trail for a single B2B invoice escalation process."""
    return (
        db.query(RecoveryAttempt)
        .filter(RecoveryAttempt.invoice_id == invoice_id)
        .order_by(RecoveryAttempt.attempt_number)
        .all()
    )


@router.get("/stats")
def get_invoice_stats(db: Session = Depends(get_db)):
    """Get B2B receivables aggregate metrics."""
    total_overdue = db.query(func.sum(Invoice.amount)).filter(Invoice.status.in_(["open", "escalated"])).scalar() or 0.0
    avg_days_to_collection = db.query(func.avg(Invoice.days_overdue)).filter(Invoice.status == "paid").scalar() or 0.0

    # Count by status
    status_counts = dict(db.query(Invoice.status, func.count(Invoice.id)).group_by(Invoice.status).all())

    return {
        "total_overdue": float(total_overdue),
        "avg_days_to_collection": float(avg_days_to_collection),
        "status_counts": {
            "open": status_counts.get("open", 0),
            "paid": status_counts.get("paid", 0),
            "escalated": status_counts.get("escalated", 0),
            "written_off": status_counts.get("written_off", 0),
        }
    }
