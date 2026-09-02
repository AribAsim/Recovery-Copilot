# LLM Classifier Evaluation Results
### Summary Metrics
- **Overall Accuracy**: 96.0% (48/50)
- **LLM-Only Accuracy**: 96.0% (48/50)
- **Deterministic Fallback Accuracy**: 0.0% (0/0)
- **Average Confidence (Correct)**: 0.98
- **Average Confidence (Incorrect)**: 0.93

### Precision and Recall per Category
| Category | Precision | Recall | True Positives (TP) | False Positives (FP) | False Negatives (FN) |
| --- | --- | --- | --- | --- | --- |
| bank_server_down | 0.86 | 0.86 | 6 | 1 | 1 |
| card_declined_generic | 1.00 | 1.00 | 6 | 0 | 0 |
| expired_card | 1.00 | 1.00 | 7 | 0 | 0 |
| insufficient_funds | 1.00 | 1.00 | 7 | 0 | 0 |
| invalid_cvv | 1.00 | 1.00 | 11 | 0 | 0 |
| network_timeout | 0.80 | 0.80 | 4 | 1 | 1 |
| unknown | 0.00 | 0.00 | 0 | 0 | 0 |
| user_abandoned | 1.00 | 1.00 | 7 | 0 | 0 |

### Confusion Matrix
| True \ Pred | bank_server_down | card_declined_generic | expired_card | insufficient_funds | invalid_cvv | network_timeout | unknown | user_abandoned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bank_server_down | 6 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| card_declined_generic | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| expired_card | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| insufficient_funds | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 |
| invalid_cvv | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 |
| network_timeout | 1 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| user_abandoned | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |

### Detail Log
| Raw Text | True Category | Predicted Category | Confidence | Mode Used | Correct? | Reasoning |
| --- | --- | --- | --- | --- | --- | --- |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| declined due to low funds | insufficient_funds | insufficient_funds | 1.00 | llm | Yes | AI classified the payment failure as insufficient funds. |
| read timeout from upstream | network_timeout | network_timeout | 0.99 | llm | Yes | AI classified the payment failure as network timeout. |
| EXPIRED_CARD | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| decline: CVV mismatch | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| decline 51 | insufficient_funds | insufficient_funds | 0.95 | llm | Yes | AI classified the payment failure as insufficient funds. |
| 96 - System Malfunction | bank_server_down | bank_server_down | 0.95 | llm | Yes | AI classified the payment failure as bank server down. |
| NSF Decline | insufficient_funds | insufficient_funds | 1.00 | llm | Yes | AI classified the payment failure as insufficient funds. |
| decline: card has expired | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| abandoned by customer during auth | user_abandoned | user_abandoned | 0.99 | llm | Yes | AI classified the payment failure as user abandoned. |
| Not enough balance to complete transaction | insufficient_funds | insufficient_funds | 1.00 | llm | Yes | AI classified the payment failure as insufficient funds. |
| the card has reached its expiration date | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| decline: CVV mismatch | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| 96 System error / bank down | bank_server_down | bank_server_down | 0.99 | llm | Yes | AI classified the payment failure as bank server down. |
| bank server is down/offline | bank_server_down | bank_server_down | 1.00 | llm | Yes | AI classified the payment failure as bank server down. |
| 91 - System Error / Timeout | network_timeout | network_timeout | 0.99 | llm | Yes | AI classified the payment failure as network timeout. |
| card declined by issuing bank | card_declined_generic | card_declined_generic | 0.95 | llm | Yes | AI classified the payment failure as card declined generic. |
| incorrect details | invalid_cvv | invalid_cvv | 0.70 | llm | Yes | AI classified the payment failure as invalid cvv. |
| connection reset by peer | network_timeout | network_timeout | 0.90 | llm | Yes | AI classified the payment failure as network timeout. |
| decline: card has expired | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| 05 Generic decline | card_declined_generic | card_declined_generic | 0.95 | llm | Yes | AI classified the payment failure as card declined generic. |
| NSF Decline | insufficient_funds | insufficient_funds | 0.99 | llm | Yes | AI classified the payment failure as insufficient funds. |
| Issuer Down | bank_server_down | bank_server_down | 0.98 | llm | Yes | AI classified the payment failure as bank server down. |
| upstream service unavailable | network_timeout | bank_server_down | 0.90 | llm | No | AI classified the payment failure as bank server down. |
| User navigated back from checkout page | user_abandoned | user_abandoned | 0.99 | llm | Yes | AI classified the payment failure as user abandoned. |
| 05 - Do Not Honor | card_declined_generic | card_declined_generic | 0.95 | llm | Yes | AI classified the payment failure as card declined generic. |
| card verification code incorrect | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| session expired on OTP screen | user_abandoned | user_abandoned | 0.90 | llm | Yes | AI classified the payment failure as user abandoned. |
| Issuer Down | bank_server_down | bank_server_down | 0.98 | llm | Yes | AI classified the payment failure as bank server down. |
| User navigated back from checkout page | user_abandoned | user_abandoned | 0.99 | llm | Yes | AI classified the payment failure as user abandoned. |
| card issuer declined this charge | card_declined_generic | card_declined_generic | 0.95 | llm | Yes | AI classified the payment failure as card declined generic. |
| customer dropped off | user_abandoned | user_abandoned | 0.99 | llm | Yes | AI classified the payment failure as user abandoned. |
| canceled by customer | user_abandoned | user_abandoned | 0.99 | llm | Yes | AI classified the payment failure as user abandoned. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| account has insufficient funds for payment | insufficient_funds | insufficient_funds | 1.00 | llm | Yes | AI classified the payment failure as insufficient funds. |
| 54 Card expired | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| 51 Insufficient funds / over limit | insufficient_funds | insufficient_funds | 1.00 | llm | Yes | AI classified the payment failure as insufficient funds. |
| DO_NOT_HONOR | card_declined_generic | card_declined_generic | 0.95 | llm | Yes | AI classified the payment failure as card declined generic. |
| decline: bank unavailable | bank_server_down | bank_server_down | 0.98 | llm | Yes | AI classified the payment failure as bank server down. |
| remote system failed to respond | bank_server_down | network_timeout | 0.95 | llm | No | AI classified the payment failure as network timeout. |
| 05 Generic decline | card_declined_generic | card_declined_generic | 1.00 | llm | Yes | AI classified the payment failure as card declined generic. |
| exipred card info provided | expired_card | expired_card | 0.99 | llm | Yes | AI classified the payment failure as expired card. |
| read timeout from upstream | network_timeout | network_timeout | 0.99 | llm | Yes | AI classified the payment failure as network timeout. |
| security code check failed | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| CVC/CVV2 error | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.99 | llm | Yes | AI classified the payment failure as invalid cvv. |
| customer clicked cancel | user_abandoned | user_abandoned | 1.00 | llm | Yes | AI classified the payment failure as user abandoned. |
| card status: expired | expired_card | expired_card | 1.00 | llm | Yes | AI classified the payment failure as expired card. |
| INVALID_CVV | invalid_cvv | invalid_cvv | 1.00 | llm | Yes | AI classified the payment failure as invalid cvv. |
