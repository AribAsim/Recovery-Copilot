# Controlled Benchmarking Strategy Evaluation
This report evaluates 5 recovery strategies against identical simulated populations of 100 transactions across 4 failure mixes.
## Scenario Scenario: BASELINE
| Strategy | Recovery Rate | Gross Recovered | Recovery Cost | Net Recovered | Escalation Rate | Avg Attempts |
| --- | --- | --- | --- | --- | --- | --- |
| No Action | 0.0% | ₹0 | ₹0.0 | **₹0.0** | 0.0% | 0.0 |
| Always Retry | 88.0% | ₹482,224.3 | ₹0.0 | **₹482,224.3** | 0.0% | 1.76 |
| Always Nudge | 78.0% | ₹438,624.12 | ₹98.0 | **₹438,526.12** | 0.0% | 1.96 |
| Rule-Based Recovery Copilot | 86.0% | ₹471,499.98 | ₹932.0 | **₹470,567.98** | 6.0% | 1.74 |
| AI-Assisted Recovery Copilot | 95.0% | ₹516,594.92 | ₹50.0 | **₹516,544.92** | 0.0% | 1.44 |

## Scenario Scenario: CARD_HEAVY
| Strategy | Recovery Rate | Gross Recovered | Recovery Cost | Net Recovered | Escalation Rate | Avg Attempts |
| --- | --- | --- | --- | --- | --- | --- |
| No Action | 0.0% | ₹0 | ₹0.0 | **₹0.0** | 0.0% | 0.0 |
| Always Retry | 88.0% | ₹458,007.83 | ₹0.0 | **₹458,007.83** | 0.0% | 1.76 |
| Always Nudge | 78.0% | ₹426,606.83 | ₹98.0 | **₹426,508.83** | 0.0% | 1.96 |
| Rule-Based Recovery Copilot | 88.0% | ₹465,052.36 | ₹510.5 | **₹464,541.86** | 3.0% | 1.64 |
| AI-Assisted Recovery Copilot | 95.0% | ₹503,878.08 | ₹50.0 | **₹503,828.08** | 0.0% | 1.44 |

## Scenario Scenario: INFRA_HEAVY
| Strategy | Recovery Rate | Gross Recovered | Recovery Cost | Net Recovered | Escalation Rate | Avg Attempts |
| --- | --- | --- | --- | --- | --- | --- |
| No Action | 0.0% | ₹0 | ₹0.0 | **₹0.0** | 0.0% | 0.0 |
| Always Retry | 88.0% | ₹458,007.83 | ₹0.0 | **₹458,007.83** | 0.0% | 1.76 |
| Always Nudge | 78.0% | ₹426,606.83 | ₹98.0 | **₹426,508.83** | 0.0% | 1.96 |
| Rule-Based Recovery Copilot | 89.0% | ₹459,902.05 | ₹471.5 | **₹459,430.55** | 3.0% | 1.76 |
| AI-Assisted Recovery Copilot | 95.0% | ₹503,878.08 | ₹50.0 | **₹503,828.08** | 0.0% | 1.44 |

## Scenario Scenario: AMBIGUOUS_HEAVY
| Strategy | Recovery Rate | Gross Recovered | Recovery Cost | Net Recovered | Escalation Rate | Avg Attempts |
| --- | --- | --- | --- | --- | --- | --- |
| No Action | 0.0% | ₹0 | ₹0.0 | **₹0.0** | 0.0% | 0.0 |
| Always Retry | 88.0% | ₹482,224.3 | ₹0.0 | **₹482,224.3** | 0.0% | 1.76 |
| Always Nudge | 78.0% | ₹438,624.12 | ₹98.0 | **₹438,526.12** | 0.0% | 1.96 |
| Rule-Based Recovery Copilot | 53.0% | ₹293,059.42 | ₹6,031.0 | **₹287,028.42** | 40.0% | 2.22 |
| AI-Assisted Recovery Copilot | 95.0% | ₹516,594.92 | ₹50.0 | **₹516,544.92** | 0.0% | 1.44 |

