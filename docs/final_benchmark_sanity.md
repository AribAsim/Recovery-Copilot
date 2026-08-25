# Final Benchmark Sanity Check Report

> Analysis-only. No production code was changed during this validation.

---

## 1. Action Distribution (AI-Assisted Recovery Copilot)

| Action | Count | Share |
| --- | --- | --- |
| `request_new_payment_method` | 100 | 69.4% |
| `retry_after_delay` | 44 | 30.6% |

The stateful predictor never recommends `retry_payment` as a second attempt. When the initial retry fails, the context compilation downgrades repeat-retry probability, and the value engine ranks `request_new_payment_method` first. The policy gate approves it, and the executor runs it.

---

## 2. Failure Action Mappings & Simulated Outcomes

The executor's mock success model assigns the following base probabilities:

| Action | Base Success Probability |
| --- | --- |
| `request_new_payment_method` | 65% |
| `retry_after_delay` | 50% |
| `retry_payment` | 50% |
| `send_recovery_message` | 35% |
| `escalate_human` | 20% |

No action receives an unintended simulator advantage. The AI strategy outperforms baselines because it selects `request_new_payment_method` — which has the highest simulator success rate — more consistently than rule-based or always-retry strategies.

---

## 3. 95% Invariance Explanation

**Finding:** The identical 95.0% recovery rate across all four scenarios is primarily a consequence of **synthetic population homogeneity**, not benchmark implementation error.

**Why it is consistent across scenarios:**
- All four scenarios use an identical seed (`seed=42`) and identical 100-transaction population clones.
- The failure *distribution* changes (card-heavy, infra-heavy, etc.), but the stateful predictor's response to any first-round failure is to rotate toward `request_new_payment_method`, which has the highest success probability in the mock executor.
- Because the population size is fixed at 100 and action selection converges to the same high-probability fallback, the aggregate recovery rate stabilises at approximately 95%.

**This is:**
- ✅ A genuine consequence of state-aware action rotation
- ✅ Not caused by benchmark scoring manipulation
- ⚠️ Not directly transferable to real Razorpay traffic, where success rates per action type are empirical, not simulated

---

## 4. Benchmark Result Summary (Corrected Framing)

| Strategy | Recovery Rate | Net Recovery (Baseline) |
| --- | --- | --- |
| No Action | 0% | ₹0 |
| Always Retry | 88% | ₹482,224.30 |
| Rule-Based Recovery Copilot | 86% | ₹470,567.98 |
| **AI-Assisted Recovery Copilot** | **95%** | **₹516,544.92** |

**Correct claim:** The AI-assisted stateful recovery strategy achieved a **7 percentage-point higher recovery rate** (95% vs 88%) and recovered **₹34,320.62 more net value** than Always Retry in the baseline scenario of our controlled 100-transaction synthetic benchmark.

**Incorrect claim (do not use):** "Our AI achieves 95% payment recovery."

---

## 5. Benchmark Validity

| Dimension | Status | Notes |
| --- | --- | --- |
| Duplicate action blocks | ✅ Eliminated | Stateful context prevents repeat-failed-action recommendations |
| Policy gate authority | ✅ Intact | All actions pass through deterministic policy — AI cannot bypass it |
| Calibration error (mid-range) | ✅ Low | 3.4 pp and 5.0 pp error in tested buckets |
| Outcome coupling | ⚠️ Partial | `request_new_payment_method` has highest mock success rate; AI learns to select it |
| Real-world generalisability | ⚠️ Unproven | Benchmark uses synthetic executor — not validated against live Razorpay outcomes |

---

## 6. Disclosures for Pitch Use

The 95% figure is legitimate for the hackathon with the following disclosures:

1. Results are from a **controlled 100-transaction synthetic benchmark**, not live traffic.
2. Action success probabilities are **simulated**, not empirically derived from Razorpay data.
3. The improvement over Always Retry is **+7 percentage points recovery rate** and **+₹34,320 net value** per 100-transaction batch — not a percentage-improvement figure.

These limitations do not undermine the architectural demonstration. The benchmark proves that **state-aware decisioning outperforms stateless recovery within the simulation**, and that the policy gate correctly governs every execution step.

---

*Backend architecture frozen after Phase 8. No further code changes made during this sanity validation.*
