"""
Diagnostic validation runner.
Performs verification queries on the sqlite database to resolve
confidence vs probability definitions, duplicate actions, and traces records end-to-end.
"""
import sys
import os
import json
import collections

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.models import Transaction, RecoveryAttempt

def validate_integrity():
    print("Initiating Diagnostic Integrity Validation...")
    db = SessionLocal()
    
    # 1. Trace 5 records
    attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.reasoning.like("%AI-Assisted Recovery%")).limit(5).all()
    
    trace_data = []
    for att in attempts:
        trace_data.append({
            "attempt_id": att.id,
            "transaction_id": att.transaction_id,
            "attempt_number": att.attempt_number,
            "diagnosis": att.diagnosis,
            "confidence": att.confidence,
            "ai_confidence": att.ai_confidence,
            "ai_predicted_probability": att.ai_predicted_probability,
            "ai_recommendation": att.ai_recommendation,
            "policy_decision": att.policy_decision,
            "policy_block_reason": att.policy_block_reason,
            "approved_action": att.approved_action,
            "outcome": att.outcome
        })
        
    # 2. Check duplicate action counts
    dup_attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.policy_block_reason.like("%Duplicate action check failed%")).all()
    dup_details = []
    for att in dup_attempts[:10]:
        txn = db.query(Transaction).filter(Transaction.id == att.transaction_id).first()
        prev_actions = [p.action_taken for p in txn.attempts if p.attempt_number < att.attempt_number]
        dup_details.append({
            "txn_id": txn.id,
            "attempt_number": att.attempt_number,
            "recommendation": att.ai_recommendation,
            "approved_action": att.approved_action,
            "prev_actions": prev_actions,
            "block_reason": att.policy_block_reason
        })

    # Output detailed Markdown verification
    report = []
    report.append("# Diagnostic Integrity Validation Report\n")
    
    report.append("## 1. Field Definitions Map\n")
    report.append("| Field Name | Source | Meaning | Expected Range | DB Column | Producer | Consumer |\n")
    report.append("| --- | --- | --- | --- | --- | --- | --- |\n")
    report.append("| `confidence` | Diagnosis | Confidence of payment failure type classification | 0.0 - 1.0 | `confidence` | Classifier | Policy Gate |\n")
    report.append("| `ai_confidence` | Predictor | Confidence of target prediction choice recommendation | 0.0 - 1.0 | `ai_confidence` | Predictor | DB/Audit |\n")
    report.append("| `ai_predicted_probability` | Predictor | Estimated chance that the recommended action succeeds | 0.0 - 1.0 | `ai_predicted_probability` | Predictor | DB/Audit |\n")
    report.append("| `expected_recovery_value` | Value Engine | Calculated mathematical net recovery expectancy | Real Float | `expected_recovery_value` | Value Engine | DB/Audit |\n")

    report.append("\n## 2. Confidence and Probability Stats (Independent Calculation)\n")
    all_ai = db.query(RecoveryAttempt).filter(RecoveryAttempt.reasoning.like("%AI-Assisted Recovery%")).all()
    confs = [a.ai_confidence for a in all_ai if a.ai_confidence is not None]
    probs = [a.ai_predicted_probability for a in all_ai if a.ai_predicted_probability is not None]
    
    if confs:
        report.append(f"- **AI Confidence Range**: Min={min(confs):.2f}, Max={max(confs):.2f}, Mean={sum(confs)/len(confs):.2f}\n")
    else:
        report.append("- **AI Confidence**: No non-null values found.\n")
        
    if probs:
        report.append(f"- **Predicted Probability Range**: Min={min(probs):.2f}, Max={max(probs):.2f}, Mean={sum(probs)/len(probs):.2f}\n")
    else:
        report.append("- **Predicted Probability**: No non-null values found.\n")

    report.append("\n## 3. End-to-End 5-Record Audit Trace\n")
    for td in trace_data:
        report.append(f"### Attempt ID: {td['attempt_id']} (Transaction: {td['transaction_id']})\n")
        report.append(f"- Attempt round: {td['attempt_number']}\n")
        report.append(f"- Diagnosis classification: `{td['diagnosis']}` (confidence: {td['confidence']})\n")
        report.append(f"- AI Predictor Confidence: {td['ai_confidence']} | Probability: {td['ai_predicted_probability']}\n")
        report.append(f"- AI Recommendation: `{td['ai_recommendation']}`\n")
        report.append(f"- Policy Gate Decision: `{td['policy_decision']}` (Reason: {td['policy_block_reason']})\n")
        report.append(f"- Executor Approved Action: `{td['approved_action']}` → Outcome: `{td['outcome']}`\n\n")

    report.append("\n## 4. Duplicate Action Override Analysis\n")
    report.append("| Txn ID | Round | AI Recommendation | Previous Actions | Override Result |\n")
    report.append("| --- | --- | --- | --- | --- |\n")
    for d in dup_details:
        report.append(f"| {d['txn_id']} | {d['attempt_number']} | `{d['recommendation']}` | {d['prev_actions']} | {d['block_reason']} |\n")

    report.append("\n## 5. Primary Escalation Attribution\n")
    escalated_attempts = db.query(RecoveryAttempt).filter(RecoveryAttempt.policy_decision == "REJECTED").all()
    primary_rules = collections.Counter()
    for att in escalated_attempts:
        if att.policy_block_reason:
            if "Duplicate action check failed" in att.policy_block_reason:
                primary_rules["Duplicate Action blocked"] += 1
            elif "confidence" in att.policy_block_reason:
                primary_rules["Confidence Below Threshold"] += 1
            elif "Maximum retry" in att.policy_block_reason:
                primary_rules["Max attempts reached"] += 1
            else:
                primary_rules[att.policy_block_reason] += 1
        else:
            primary_rules["Unknown"] += 1
            
    report.append("| Escalation Primary Cause | Count | Share |\n")
    report.append("| --- | --- | --- |\n")
    total_esc = len(escalated_attempts)
    for rule, count in primary_rules.items():
        share = (count / total_esc * 100) if total_esc else 0.0
        report.append(f"| {rule} | {count} | {share:.1f}% |\n")

    report.append("\n## 6. Corrected Calibration Analysis\n")
    # Calibration calculation directly matching predicted probability bucket with actual outcomes
    buckets = {
        "0-20%": [], "20-40%": [], "40-60%": [], "60-80%": [], "80-100%": []
    }
    for att in all_ai:
        prob = att.ai_predicted_probability or 0.0
        pct = prob * 100.0
        if 0.0 <= pct < 20.0:
            k = "0-20%"
        elif 20.0 <= pct < 40.0:
            k = "20-40%"
        elif 40.0 <= pct < 60.0:
            k = "40-60%"
        elif 60.0 <= pct < 80.0:
            k = "60-80%"
        else:
            k = "80-100%"
        buckets[k].append(att)
        
    report.append("| Probability Bucket | Attempt Count | Average Predicted Probability | Actual Recovery Rate | Calibration Error |\n")
    report.append("| --- | --- | --- | --- | --- |\n")
    for k, items in buckets.items():
        if not items:
            report.append(f"| {k} | 0 | 0.0% | 0.0% | 0.0% |\n")
            continue
        sum_p = sum(i.ai_predicted_probability for i in items if i.ai_predicted_probability is not None)
        mean_p = sum_p / len(items)
        sum_recovered = sum(1 for i in items if i.outcome == "recovered")
        act_rec = sum_recovered / len(items)
        err = abs(mean_p - act_rec)
        report.append(f"| {k} | {len(items)} | {mean_p*100:.1f}% | {act_rec*100:.1f}% | {err*100:.1f}% |\n")

    # Save to file
    with open("docs/ai_benchmark_diagnosis.md", "a", encoding="utf-8") as f:
        f.writelines(report)
        
    db.close()
    print("Verification report successfully appended to docs/ai_benchmark_diagnosis.md")

if __name__ == "__main__":
    validate_integrity()
