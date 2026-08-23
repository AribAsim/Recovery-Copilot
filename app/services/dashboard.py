from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Transaction, RecoveryAttempt


def get_summary(db: Session) -> dict:
    total_txns = db.query(Transaction).count()
    recovered = db.query(Transaction).filter(Transaction.status == "recovered").all()
    lost = db.query(Transaction).filter(Transaction.status == "lost").count()
    escalated_terminal = db.query(Transaction).filter(Transaction.status == "escalated").count()
    pending = db.query(Transaction).filter(Transaction.status == "pending").count()
    escalated = db.query(RecoveryAttempt).filter(RecoveryAttempt.escalated == True).count()  # noqa: E712
    promise_to_pay_count = db.query(Transaction).filter(Transaction.promise_to_pay == True).count()  # noqa: E712
    promised_amount_total = db.query(func.sum(Transaction.promised_amount)).filter(Transaction.promise_to_pay == True).scalar() or 0.0

    gross_recovered = sum(t.amount for t in recovered)
    total_cost = db.query(func.sum(RecoveryAttempt.cost)).scalar() or 0.0
    net_recovered = gross_recovered - total_cost

    at_risk = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status.in_(["failed", "pending", "lost", "escalated"])
    ).scalar() or 0.0

    by_failure_type = {}
    for code, in db.query(Transaction.failure_code).distinct():
        subset = db.query(Transaction).filter(Transaction.failure_code == code).all()
        rec = sum(1 for t in subset if t.status == "recovered")
        by_failure_type[code] = {
            "total": len(subset),
            "recovered": rec,
            "recovery_rate": round(rec / len(subset), 3) if subset else 0.0,
        }

    # Action breakdown for donut chart
    attempts = db.query(RecoveryAttempt.action_taken).all()
    action_counts = {
        "retry": 0,
        "nudge": 0,
        "new_method": 0,
        "escalate": 0,
    }
    for (action,) in attempts:
        if action in ("retry_immediate", "retry_in_24h"):
            action_counts["retry"] += 1
        elif action == "send_nudge":
            action_counts["nudge"] += 1
        elif action == "request_new_method":
            action_counts["new_method"] += 1
        elif action == "escalate_human":
            action_counts["escalate"] += 1

    return {
        "total_transactions": total_txns,
        "recovered_count": len(recovered),
        "lost_count": lost,
        "escalated_terminal_count": escalated_terminal,
        "pending_count": pending,
        "escalated_count": escalated,
        "gross_amount_recovered": round(gross_recovered, 2),
        "total_action_cost": round(total_cost, 2),
        "net_amount_recovered": round(net_recovered, 2),
        "amount_still_at_risk": round(at_risk, 2),
        "promise_to_pay_count": promise_to_pay_count,
        "promised_amount_total": round(promised_amount_total, 2),
        "overall_recovery_rate": round(len(recovered) / total_txns, 3) if total_txns else 0.0,
        "by_failure_type": by_failure_type,
        "action_counts": action_counts,
    }

