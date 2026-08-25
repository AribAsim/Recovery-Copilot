# 5-Minute B2B Revenue Recovery Copilot Pitch Script

> **Goal:** Rehearse to complete within 4:40 to 4:50 to ensure perfect timing with natural pauses and UI transitions.

---

## 0:00–0:35 — The Core Problem
"In modern payment gateways, payments fail. They fail due to bank timeouts, expired cards, or customer drop-offs. But payments don't remain unrecovered because recovery is impossible. They fail because the *next chosen recovery action* is often poorly matched. 

Traditional payment systems rely on stateless, static rule loops. If a payment fails, they blindly retry it immediately. If it fails again, they retry it again. This duplicate action spam degrades database performance, wastes transaction fees, triggers gateway spam blocks, and ultimately fails to recover the transaction."

---

## 0:35–1:10 — The Core Insight
"Our key insight is that payment recovery is not a single decision—it is a sequential game. After the first action fails, the decision space changes. The next recovery attempt has different evidence. 

Our Recovery Copilot gathers transaction context, maps attempt history, and scores candidates based on expected net value. A previously failed action isn't strictly blacklisted, but its predicted success probability is degraded. This allows the system to rotate dynamically to alternative high-value actions rather than blindly repeating failed strategies."

---

## 1:10–2:10 — The Architecture (Explain the Core thesis)
"This is our pipeline:

1. **canonical event**: Every failure generates a standard payment failure model.
2. **recovery context**: We compile metadata alongside the complete attempts history.
3. **stateful ai predictor**: Predicts recovery probabilities across a closed allowlist of actions.
4. **expected net recovery**: Calculates `(Amount * Probability) - Action Cost` to rank actions by highest expected value.
5. **deterministic policy gate**: Evaluates deterministic guardrails (cooldown checks, transaction value caps, compliance hours, and repeat limits).
6. **executor**: Executes the approved action, mapping results back to update the recovery context.

The defining safety property of this architecture is this:
> **AI recommends, but it never holds capital authority.**

Every action proposed by the predictor is forced through a deterministic policy gate. Low confidence degrades safely, and policy overrides can convert actions or route them to humans, keeping the system safe and auditable."

---

## 2:10–3:40 — Live Demo Walkthrough
"Let's trace this end-to-end on a live transaction.

[Show browser UI with transaction 101: ₹4,500, bank_server_down]

Here we have transaction 101. It has failed due to `bank_server_down` on an HDFC card.

**Step 1: First Attempt**
1. We click **Step Decision Pipeline**.
2. The AI Predictor sees `bank_server_down` (transient infra error) and recommends `retry_payment` with high expected value.
3. It passes through the Policy Gate and executes.
4. *Result:* The payment fails again. The transaction status returns to `failed`.

**Step 2: Second Attempt**
1. We click **Step Decision Pipeline** again.
2. This time, the `RecoveryContext` detects that `retry_payment` has already failed on round 1.
3. The Stateful Predictor degrades the success probability of a repeat retry by 90%.
4. Consequently, `retry_after_delay` or `request_new_payment_method` rises to the top of the ranked Expected Net Recovery.
5. The Policy Gate verifies the cooldown constraints, authorizes the new action, and the Executor runs it.
6. *Result:* The customer provides a new card, and the payment is successfully recovered!

By integrating history directly into the context, the copilot avoided repeating a failed action and successfully saved the transaction."

---

## 3:40–4:20 — Controlled Benchmark Evidence
"To validate this architecture, we ran a controlled 100-transaction synthetic benchmark evaluating our stateful strategy against standard payment recovery baselines.

| Strategy | Recovery Rate | Net Recovery (Baseline) |
| --- | --- | --- |
| Always Retry | 88% | ₹482,224.30 |
| Rule-Based Copilot | 86% | ₹470,567.98 |
| **AI-Assisted Copilot** | **95%** | **₹516,544.92** |

On this benchmark, the stateful AI recovery strategy achieved a **95% recovery rate** and **₹516,544.92 net recovery**, compared with 88% and ₹482,224 for Always Retry. This yields a **7 percentage-point recovery-rate advantage** and **₹34,320.62 in additional net value** recovered per 100 transactions.

*Disclosure: These are controlled simulation results to evaluate decisioning logic, not a claim about live production recovery rates.*"

---

## 4:20–5:00 — Why Razorpay Cares (Closing)
"Our Copilot is built for live billing platforms like Razorpay. 

By separating AI-driven value maximization from deterministic policy authorization, we create a system that can be deployed safely without risking compliance breaches. 

This isn't an unconstrained LLM deciding what happens to payment flows. It is an AI recovery copilot operating inside strict, deterministic financial controls. Every decision is explainable, every action is logged, and every outcome makes the next recovery decision smarter.

Thank you."
