"""
Benchmarking Harness.
Compares five strategies on the EXACT SAME generated populations of transactions:
1. No Action
2. Always Retry (retry_payment)
3. Always Nudge (send_recovery_message)
4. Rule-Based Recovery Copilot (Deterministic lookup)
5. AI-Assisted Recovery Copilot (AI context predictions passed through Policy Gate)

Evaluated across four failure scenarios (baseline, card_heavy, infra_heavy, ambiguous_heavy).
"""

import sys
import os
import random
import json
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, Base, engine
from app.models.models import Transaction, RecoveryAttempt
from app.services.data_generator import generate_batch, SCENARIOS
from app.services.engine import process_transaction
from app.services.policy_engine import evaluate as evaluate_policy, PolicyContext
from app.services.action_executor import RecoveryActionExecutor
from app.core.config import settings

# Explicit Mock Constants for strict comparison
SIM_SUCCESS = {
    "retry_payment": 0.50,
    "retry_after_delay": 0.55,
    "request_new_payment_method": 0.65,
    "send_recovery_message": 0.35,
    "escalate_human": 0.20,
    "no_action": 0.0,
    "give_up": 0.0
}

def clone_population(txns):
    clones = []
    for t in txns:
        clones.append({
            "customer_id": t.customer_id,
            "amount": t.amount,
            "failure_code": t.failure_code,
            "raw_failure_text": t.raw_failure_text,
            # Canonical Fields
            "payment_id": t.payment_id,
            "order_id": t.order_id,
            "currency": t.currency,
            "payment_method": t.payment_method,
            "failure_source": t.failure_source,
            "failure_step": t.failure_step,
            "failure_reason": t.failure_reason,
            "gateway": t.gateway,
            "bank": t.bank,
            "checkout_state": t.checkout_state
        })
    return clones

def run_strategy(strategy_name, population_data, seed=42):
    """
    Executes a single recovery strategy against a cloned population of transactions.
    """
    random.seed(seed)
    db = SessionLocal()
    # Reset DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Hydrate database with the exact clone list
    txns = []
    for data in population_data:
        txn = Transaction(
            customer_id=data["customer_id"],
            amount=data["amount"],
            failure_code=data["failure_code"],
            raw_failure_text=data["raw_failure_text"],
            status="failed",
            attempts_count=0,
            payment_id=data["payment_id"],
            order_id=data["order_id"],
            currency=data["currency"],
            payment_method=data["payment_method"],
            failure_source=data["failure_source"],
            failure_step=data["failure_step"],
            failure_reason=data["failure_reason"],
            gateway=data["gateway"],
            bank=data["bank"],
            checkout_state=data["checkout_state"]
        )
        db.add(txn)
        txns.append(txn)
    db.commit()
    for t in txns:
        db.refresh(t)

    # Execute loops until terminal (up to MAX_RETRY_ATTEMPTS)
    max_loops = settings.MAX_RETRY_ATTEMPTS
    executor = RecoveryActionExecutor(action_costs=settings.ACTION_COST)

    for attempt_round in range(max_loops):
        open_txns = db.query(Transaction).filter(Transaction.status.in_(["failed", "pending"])).all()
        if not open_txns:
            break

        for txn in open_txns:
            # Determine logic action
            if strategy_name == "No Action":
                # Instantly lost
                txn.status = "lost"
                db.commit()
                continue
            
            elif strategy_name == "Always Retry":
                action = "retry_payment"
            
            elif strategy_name == "Always Nudge":
                action = "send_recovery_message"
            
            elif strategy_name == "Rule-Based Recovery Copilot":
                # Use deterministic router
                from app.services.decision_router import decide_action
                raw_action, _ = decide_action(txn.failure_code, 0.95, 0.70)
                action_map = {
                    "retry_immediate": "retry_payment",
                    "retry_in_24h": "retry_after_delay",
                    "request_new_method": "request_new_payment_method",
                    "send_nudge": "send_recovery_message",
                    "escalate_human": "escalate_human"
                }
                action = action_map.get(raw_action, "escalate_human")
            
            elif strategy_name == "AI-Assisted Recovery Copilot":
                # Build Recovery Context
                from app.services.recovery_context import RecoveryContext, HistoricalAttempt
                from app.services.stateful_predictor import StatefulPredictor
                from app.services.recovery_value import CandidateAction, compute_expected_value
                
                attempts_history = []
                actions_attempted = []
                actions_failed = []
                actions_succeeded = []
                last_timestamp = None
                
                # Fetch attempts belonging to this txn so far during strategy loop
                for att in txn.attempts:
                    attempts_history.append(
                        HistoricalAttempt(
                            attempt_number=att.attempt_number,
                            action_taken=att.action_taken,
                            outcome=att.outcome,
                            timestamp=att.timestamp,
                            cost=att.cost or 0.0,
                            recovery_amount=att.actual_outcome_amount or 0.0
                        )
                    )
                    actions_attempted.append(att.action_taken)
                    if att.outcome == "failed":
                        actions_failed.append(att.action_taken)
                    elif att.outcome == "recovered":
                        actions_succeeded.append(att.action_taken)
                    last_timestamp = att.timestamp
                    
                time_since = None
                if last_timestamp:
                    time_since = (datetime.utcnow() - last_timestamp).total_seconds()
                    
                # Policy Context
                from datetime import datetime
                context = PolicyContext(
                    current_time=datetime.utcnow(),
                    high_value_threshold=50000.0,
                    confidence_threshold=0.70,
                    max_retry_attempts=settings.MAX_RETRY_ATTEMPTS
                )
                
                rec_context = RecoveryContext(
                    transaction_id=txn.id,
                    amount=txn.amount,
                    currency=txn.currency or "INR",
                    payment_method=txn.payment_method or "card",
                    failure_source=txn.failure_source or "customer",
                    failure_step=txn.failure_step or "payment_authorization",
                    failure_reason=txn.failure_reason or "insufficient_funds",
                    failure_code=txn.failure_code or "insufficient_funds",
                    attempt_number=txn.attempts_count + 1,
                    checkout_state=txn.checkout_state,
                    attempts_history=attempts_history,
                    actions_attempted=actions_attempted,
                    actions_failed=actions_failed,
                    actions_succeeded=actions_succeeded,
                    remaining_attempts=max(0, context.max_retry_attempts - txn.attempts_count),
                    time_since_last_attempt=time_since
                )

                predictor = StatefulPredictor()
                candidates = predictor.predict_candidates(txn, rec_context)
                
                valued_actions = compute_expected_value(txn.amount, candidates, settings.ACTION_COST)
                best_candidate = valued_actions[0] if valued_actions else None
                recommendation = best_candidate.action if best_candidate else "escalate_human"
                selected_ev = best_candidate.expected_value if best_candidate else 0.0
                predicted_prob = best_candidate.probability if best_candidate else 0.0
                ai_conf_score = next((c.confidence for c in candidates if c.action == recommendation), 0.95)

                # Policy gate determines the approved action
                policy_dec = evaluate_policy(
                    recommendation=recommendation,
                    predicted_probability=predicted_prob,
                    confidence=0.95,
                    candidate_actions=candidates,
                    transaction=txn,
                    context=context
                )
                action = policy_dec.approved_action

            # Cost and execution mapping
            cost = settings.ACTION_COST.get(action, 0.0)
            outcome_res = executor.execute(action, txn)

            # Re-run evaluate_policy to capture rules evaluated for diagnosis logs if AI-assisted
            rules_eval_str = None
            pol_dec_val = None
            pol_reason = None
            app_act = None
            if strategy_name == "AI-Assisted Recovery Copilot":
                rules_eval_str = json.dumps([
                    {"rule": r.rule, "passed": r.passed, "detail": r.detail}
                    for r in policy_dec.rules_evaluated
                ])
                pol_dec_val = "REJECTED" if policy_dec.blocked else "APPROVED"
                pol_reason = policy_dec.override_reason
                app_act = policy_dec.approved_action
            
            # Log Recovery Attempt
            attempt = RecoveryAttempt(
                transaction_id=txn.id,
                attempt_number=txn.attempts_count + 1,
                diagnosis=txn.failure_code,
                confidence=0.95,
                action_taken=action,
                reasoning=f"Strategy: {strategy_name}",
                cost=cost,
                outcome=outcome_res.outcome,
                escalated=outcome_res.escalated,
                actual_outcome_amount=outcome_res.recovery_amount,
                net_recovery=outcome_res.net_recovery,
                rules_evaluated=rules_eval_str,
                ai_predicted_probability=predicted_prob if strategy_name == "AI-Assisted Recovery Copilot" else SIM_SUCCESS.get(action, 0.0),
                ai_confidence=ai_conf_score if strategy_name == "AI-Assisted Recovery Copilot" else None,
                ai_recommendation=recommendation if strategy_name == "AI-Assisted Recovery Copilot" else None,
                policy_decision=pol_dec_val,
                policy_block_reason=pol_reason,
                approved_action=app_act
            )
            db.add(attempt)

            txn.attempts_count += 1
            if outcome_res.outcome == "recovered":
                txn.status = "recovered"
            elif txn.attempts_count >= settings.MAX_RETRY_ATTEMPTS or outcome_res.outcome == "lost":
                txn.status = "escalated" if action == "escalate_human" else "lost"
            else:
                txn.status = "pending"

            db.commit()

    # Collect outcomes summary metrics
    total_txns = db.query(Transaction).count()
    recovered = db.query(Transaction).filter(Transaction.status == "recovered").all()
    lost = db.query(Transaction).filter(Transaction.status == "lost").count()
    escalated = db.query(Transaction).filter(Transaction.status == "escalated").count()
    
    gross_recovered = sum(t.amount for t in recovered)
    from sqlalchemy import func
    total_cost = db.query(func.sum(RecoveryAttempt.cost)).scalar() or 0.0
    net_recovered = gross_recovered - total_cost
    
    avg_attempts = db.query(func.avg(Transaction.attempts_count)).scalar() or 0.0
    
    db.close()
    
    return {
        "recovery_rate": round(len(recovered) / total_txns, 3) if total_txns else 0.0,
        "gross_recovered": round(gross_recovered, 2),
        "recovery_cost": round(total_cost, 2),
        "net_recovered": round(net_recovered, 2),
        "escalation_rate": round(escalated / total_txns, 3) if total_txns else 0.0,
        "avg_attempts": round(avg_attempts, 2)
    }

def run_benchmarks():
    print("Initializing controlled benchmarking experiment...")
    # Initialize a baseline database to generate population
    db = SessionLocal()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    strategies = [
        "No Action",
        "Always Retry",
        "Always Nudge",
        "Rule-Based Recovery Copilot",
        "AI-Assisted Recovery Copilot"
    ]
    
    scenarios_summary = {}

    for scen_name, mix in SCENARIOS.items():
        print(f"\nEvaluating failure distribution: {scen_name}...")
        # Generate the identical population
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        temp_txns = generate_batch(db, n=100, mix=mix, seed=42)
        population_clone = clone_population(temp_txns)
        
        scenarios_summary[scen_name] = {}
        
        for strat in strategies:
            # Run controlled strategy on cloned population
            res = run_strategy(strat, population_clone, seed=42)
            scenarios_summary[scen_name][strat] = res
            
    db.close()

    # Generate Markdown Table Report
    report = []
    report.append("# Controlled Benchmarking Strategy Evaluation\n")
    report.append("This report evaluates 5 recovery strategies against identical simulated populations of 100 transactions across 4 failure mixes.\n")
    
    for scen_name in SCENARIOS.keys():
        report.append(f"## Scenario Scenario: {scen_name.upper()}\n")
        report.append("| Strategy | Recovery Rate | Gross Recovered | Recovery Cost | Net Recovered | Escalation Rate | Avg Attempts |\n")
        report.append("| --- | --- | --- | --- | --- | --- | --- |\n")
        for strat in strategies:
            s = scenarios_summary[scen_name][strat]
            report.append(f"| {strat} | {s['recovery_rate']*100:.1f}% | ₹{s['gross_recovered']:,} | ₹{s['recovery_cost']:,} | **₹{s['net_recovered']:,}** | {s['escalation_rate']*100:.1f}% | {s['avg_attempts']} |\n")
        report.append("\n")

    # Print summary output directly
    for scen_name in SCENARIOS.keys():
        print(f"\n--- {scen_name.upper()} Benchmarks ---")
        for strat in strategies:
            s = scenarios_summary[scen_name][strat]
            print(f"{strat:30s} Recovery={s['recovery_rate']*100:5.1f}%  Net=Rs.{s['net_recovered']:10.2f} Cost=Rs.{s['recovery_cost']:8.2f} Escalation={s['escalation_rate']*100:4.1f}%")

    os.makedirs("docs", exist_ok=True)
    with open("docs/strategy_benchmarks.md", "w", encoding="utf-8") as f:
        f.writelines(report)
    print("\nBenchmark results successfully written to docs/strategy_benchmarks.md")

if __name__ == "__main__":
    run_benchmarks()
