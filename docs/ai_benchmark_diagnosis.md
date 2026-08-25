# AI Benchmark Diagnosis Report
## 1. Executive Summary
The evaluation shows that the AI-assisted recovery strategy suffers from severe underperformance due to conservative policy engine overrides, low classification confidence defaults, and retry rate bias within simulated environments.
## 2. Escalation Breakdown
| Policy Rule Triggered | Count | Percentage |
| --- | --- | --- |
| no_repeated_failed_action | 56 | 23.7% |

## 3. Prediction Calibration
| Probability Bucket | Number of Predictions | Average Predicted Recovery | Actual Recovery Rate | Calibration Error |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 195 | 21.5% | 5.1% | 16.3% |
| 40-60% | 23 | 52.0% | 47.8% | 4.1% |
| 60-80% | 18 | 65.0% | 61.1% | 3.9% |
| 80-100% | 0 | 0.0% | 0.0% | 0.0% |

## 4. Confidence Analysis
| Confidence Bucket | Transactions | Recovery Rate | Escalation Rate | Avg Predicted Probability |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 0 | 0.0% | 0.0% | 0.0% |
| 40-60% | 0 | 0.0% | 0.0% | 0.0% |
| 60-80% | 0 | 0.0% | 0.0% | 0.0% |
| 80-100% | 236 | 13.6% | 74.6% | 13.6% |

## 5. Failure-Type Analysis
| Failure Category | Transaction Count | AI Recovery | AI Escalation Rate |
| --- | --- | --- | --- |
| card_declined_generic | 120 | 0.0% | 100.0% |
| user_abandoned | 37 | 27.0% | 48.6% |
| expired_card | 21 | 28.6% | 47.6% |
| invalid_cvv | 11 | 45.5% | 36.4% |
| network_timeout | 28 | 25.0% | 50.0% |
| insufficient_funds | 12 | 25.0% | 50.0% |
| bank_server_down | 7 | 14.3% | 57.1% |

## 6. Root-Cause Diagnosis & Conclusion
- **AI Predictor Default Fallbacks**: When mock classification returns low confidence (e.g. 0.55 on `card_declined_generic`), the policy engine blocks the recommended action and forces escalation, introducing high penalty costs.
- **Retry Pricing Bias**: Retrying payments carries zero cost in the simulation. This design allows 'Always Retry' to hit high rates with no cost penalty. Real-world retries carry bank penalties or client friction costs that are not modeled.
# Diagnostic Integrity Validation Report
## 1. Field Definitions Map
| Field Name | Source | Meaning | Expected Range | DB Column | Producer | Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| `confidence` | Diagnosis | Confidence of payment failure type classification | 0.0 - 1.0 | `confidence` | Classifier | Policy Gate |
| `ai_confidence` | Predictor | Confidence of target prediction choice recommendation | 0.0 - 1.0 | `ai_confidence` | Predictor | DB/Audit |
| `ai_predicted_probability` | Predictor | Estimated chance that the recommended action succeeds | 0.0 - 1.0 | `ai_predicted_probability` | Predictor | DB/Audit |
| `expected_recovery_value` | Value Engine | Calculated mathematical net recovery expectancy | Real Float | `expected_recovery_value` | Value Engine | DB/Audit |

## 2. Confidence and Probability Stats (Independent Calculation)
- **AI Confidence**: No non-null values found.
- **Predicted Probability**: No non-null values found.

## 3. End-to-End 5-Record Audit Trace

## 4. Duplicate Action Override Analysis
| Txn ID | Round | AI Recommendation | Previous Actions | Override Result |
| --- | --- | --- | --- | --- |

## 5. Primary Escalation Attribution
| Escalation Primary Cause | Count | Share |
| --- | --- | --- |

## 6. Corrected Calibration Analysis
| Probability Bucket | Attempt Count | Average Predicted Probability | Actual Recovery Rate | Calibration Error |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 0 | 0.0% | 0.0% | 0.0% |
| 40-60% | 0 | 0.0% | 0.0% | 0.0% |
| 60-80% | 0 | 0.0% | 0.0% | 0.0% |
| 80-100% | 0 | 0.0% | 0.0% | 0.0% |
# Diagnostic Integrity Validation Report
## 1. Field Definitions Map
| Field Name | Source | Meaning | Expected Range | DB Column | Producer | Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| `confidence` | Diagnosis | Confidence of payment failure type classification | 0.0 - 1.0 | `confidence` | Classifier | Policy Gate |
| `ai_confidence` | Predictor | Confidence of target prediction choice recommendation | 0.0 - 1.0 | `ai_confidence` | Predictor | DB/Audit |
| `ai_predicted_probability` | Predictor | Estimated chance that the recommended action succeeds | 0.0 - 1.0 | `ai_predicted_probability` | Predictor | DB/Audit |
| `expected_recovery_value` | Value Engine | Calculated mathematical net recovery expectancy | Real Float | `expected_recovery_value` | Value Engine | DB/Audit |

## 2. Confidence and Probability Stats (Independent Calculation)
- **AI Confidence Range**: Min=0.95, Max=0.95, Mean=0.95
- **Predicted Probability Range**: Min=0.20, Max=0.65, Mean=0.28

## 3. End-to-End 5-Record Audit Trace
### Attempt ID: 1 (Transaction: 1)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.2
- AI Recommendation: `escalate_human`
- Policy Gate Decision: `None` (Reason: None)
- Executor Approved Action: `None` → Outcome: `escalated`

### Attempt ID: 2 (Transaction: 2)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.2
- AI Recommendation: `escalate_human`
- Policy Gate Decision: `None` (Reason: None)
- Executor Approved Action: `None` → Outcome: `escalated`

### Attempt ID: 3 (Transaction: 3)
- Attempt round: 1
- Diagnosis classification: `user_abandoned` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.35
- AI Recommendation: `send_recovery_message`
- Policy Gate Decision: `None` (Reason: None)
- Executor Approved Action: `None` → Outcome: `failed`

### Attempt ID: 4 (Transaction: 4)
- Attempt round: 1
- Diagnosis classification: `expired_card` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `None` (Reason: None)
- Executor Approved Action: `None` → Outcome: `recovered`

### Attempt ID: 5 (Transaction: 5)
- Attempt round: 1
- Diagnosis classification: `invalid_cvv` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `None` (Reason: None)
- Executor Approved Action: `None` → Outcome: `recovered`


## 4. Duplicate Action Override Analysis
| Txn ID | Round | AI Recommendation | Previous Actions | Override Result |
| --- | --- | --- | --- | --- |

## 5. Primary Escalation Attribution
| Escalation Primary Cause | Count | Share |
| --- | --- | --- |

## 6. Corrected Calibration Analysis
| Probability Bucket | Attempt Count | Average Predicted Probability | Actual Recovery Rate | Calibration Error |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 195 | 21.5% | 5.1% | 16.3% |
| 40-60% | 23 | 52.0% | 47.8% | 4.1% |
| 60-80% | 18 | 65.0% | 61.1% | 3.9% |
| 80-100% | 0 | 0.0% | 0.0% | 0.0% |
# Diagnostic Integrity Validation Report
## 1. Field Definitions Map
| Field Name | Source | Meaning | Expected Range | DB Column | Producer | Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| `confidence` | Diagnosis | Confidence of payment failure type classification | 0.0 - 1.0 | `confidence` | Classifier | Policy Gate |
| `ai_confidence` | Predictor | Confidence of target prediction choice recommendation | 0.0 - 1.0 | `ai_confidence` | Predictor | DB/Audit |
| `ai_predicted_probability` | Predictor | Estimated chance that the recommended action succeeds | 0.0 - 1.0 | `ai_predicted_probability` | Predictor | DB/Audit |
| `expected_recovery_value` | Value Engine | Calculated mathematical net recovery expectancy | Real Float | `expected_recovery_value` | Value Engine | DB/Audit |

## 2. Confidence and Probability Stats (Independent Calculation)
- **AI Confidence Range**: Min=0.95, Max=0.95, Mean=0.95
- **Predicted Probability Range**: Min=0.20, Max=0.65, Mean=0.28

## 3. End-to-End 5-Record Audit Trace
### Attempt ID: 1 (Transaction: 1)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.2
- AI Recommendation: `escalate_human`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `escalate_human` → Outcome: `escalated`

### Attempt ID: 2 (Transaction: 2)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.2
- AI Recommendation: `escalate_human`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `escalate_human` → Outcome: `escalated`

### Attempt ID: 3 (Transaction: 3)
- Attempt round: 1
- Diagnosis classification: `user_abandoned` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.35
- AI Recommendation: `send_recovery_message`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `send_recovery_message` → Outcome: `failed`

### Attempt ID: 4 (Transaction: 4)
- Attempt round: 1
- Diagnosis classification: `expired_card` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`

### Attempt ID: 5 (Transaction: 5)
- Attempt round: 1
- Diagnosis classification: `invalid_cvv` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`


## 4. Duplicate Action Override Analysis
| Txn ID | Round | AI Recommendation | Previous Actions | Override Result |
| --- | --- | --- | --- | --- |
| 3 | 2 | `send_recovery_message` | ['send_recovery_message'] | Duplicate action check failed: 'send_recovery_message' already failed. |
| 7 | 2 | `send_recovery_message` | ['send_recovery_message'] | Duplicate action check failed: 'send_recovery_message' already failed. |
| 9 | 2 | `retry_payment` | ['retry_payment'] | Duplicate action check failed: 'retry_payment' already failed. |
| 10 | 2 | `retry_after_delay` | ['retry_after_delay'] | Duplicate action check failed: 'retry_after_delay' already failed. |
| 17 | 2 | `send_recovery_message` | ['send_recovery_message'] | Duplicate action check failed: 'send_recovery_message' already failed. |
| 23 | 2 | `retry_after_delay` | ['retry_after_delay'] | Duplicate action check failed: 'retry_after_delay' already failed. |
| 25 | 2 | `retry_payment` | ['retry_payment'] | Duplicate action check failed: 'retry_payment' already failed. |
| 28 | 2 | `retry_after_delay` | ['retry_after_delay'] | Duplicate action check failed: 'retry_after_delay' already failed. |
| 30 | 2 | `request_new_payment_method` | ['request_new_payment_method'] | Duplicate action check failed: 'request_new_payment_method' already failed. |
| 34 | 2 | `retry_payment` | ['retry_payment'] | Duplicate action check failed: 'retry_payment' already failed. |

## 5. Primary Escalation Attribution
| Escalation Primary Cause | Count | Share |
| --- | --- | --- |
| Duplicate Action blocked | 56 | 100.0% |

## 6. Corrected Calibration Analysis
| Probability Bucket | Attempt Count | Average Predicted Probability | Actual Recovery Rate | Calibration Error |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 195 | 21.5% | 5.1% | 16.3% |
| 40-60% | 23 | 52.0% | 47.8% | 4.1% |
| 60-80% | 18 | 65.0% | 61.1% | 3.9% |
| 80-100% | 0 | 0.0% | 0.0% | 0.0% |
# Diagnostic Integrity Validation Report
## 1. Field Definitions Map
| Field Name | Source | Meaning | Expected Range | DB Column | Producer | Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| `confidence` | Diagnosis | Confidence of payment failure type classification | 0.0 - 1.0 | `confidence` | Classifier | Policy Gate |
| `ai_confidence` | Predictor | Confidence of target prediction choice recommendation | 0.0 - 1.0 | `ai_confidence` | Predictor | DB/Audit |
| `ai_predicted_probability` | Predictor | Estimated chance that the recommended action succeeds | 0.0 - 1.0 | `ai_predicted_probability` | Predictor | DB/Audit |
| `expected_recovery_value` | Value Engine | Calculated mathematical net recovery expectancy | Real Float | `expected_recovery_value` | Value Engine | DB/Audit |

## 2. Confidence and Probability Stats (Independent Calculation)
- **AI Confidence Range**: Min=0.95, Max=0.95, Mean=0.95
- **Predicted Probability Range**: Min=0.50, Max=0.65, Mean=0.61

## 3. End-to-End 5-Record Audit Trace
### Attempt ID: 1 (Transaction: 1)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`

### Attempt ID: 2 (Transaction: 2)
- Attempt round: 1
- Diagnosis classification: `card_declined_generic` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`

### Attempt ID: 3 (Transaction: 3)
- Attempt round: 1
- Diagnosis classification: `user_abandoned` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`

### Attempt ID: 4 (Transaction: 4)
- Attempt round: 1
- Diagnosis classification: `expired_card` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `recovered`

### Attempt ID: 5 (Transaction: 5)
- Attempt round: 1
- Diagnosis classification: `invalid_cvv` (confidence: 0.95)
- AI Predictor Confidence: 0.95 | Probability: 0.65
- AI Recommendation: `request_new_payment_method`
- Policy Gate Decision: `APPROVED` (Reason: None)
- Executor Approved Action: `request_new_payment_method` → Outcome: `failed`


## 4. Duplicate Action Override Analysis
| Txn ID | Round | AI Recommendation | Previous Actions | Override Result |
| --- | --- | --- | --- | --- |

## 5. Primary Escalation Attribution
| Escalation Primary Cause | Count | Share |
| --- | --- | --- |
| Immediate retry blocked by cooldown on sequential attempts. | 14 | 100.0% |

## 6. Corrected Calibration Analysis
| Probability Bucket | Attempt Count | Average Predicted Probability | Actual Recovery Rate | Calibration Error |
| --- | --- | --- | --- | --- |
| 0-20% | 0 | 0.0% | 0.0% | 0.0% |
| 20-40% | 0 | 0.0% | 0.0% | 0.0% |
| 40-60% | 44 | 53.4% | 56.8% | 3.4% |
| 60-80% | 100 | 65.0% | 70.0% | 5.0% |
| 80-100% | 0 | 0.0% | 0.0% | 0.0% |
