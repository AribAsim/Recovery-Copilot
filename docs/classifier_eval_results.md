# LLM Classifier Evaluation Results
### Summary Metrics
- **Overall Accuracy**: 100.0% (50/50)
- **LLM-Only Accuracy**: 0.0% (0/0)
- **Deterministic Fallback Accuracy**: 100.0% (50/50)
- **Average Confidence (Correct)**: 0.84
- **Average Confidence (Incorrect)**: 0.00

### Precision and Recall per Category
| Category | Precision | Recall | True Positives (TP) | False Positives (FP) | False Negatives (FN) |
| --- | --- | --- | --- | --- | --- |
| insufficient_funds | 1.00 | 1.00 | 7 | 0 | 0 |
| expired_card | 1.00 | 1.00 | 7 | 0 | 0 |
| network_timeout | 1.00 | 1.00 | 5 | 0 | 0 |
| bank_server_down | 1.00 | 1.00 | 7 | 0 | 0 |
| user_abandoned | 1.00 | 1.00 | 7 | 0 | 0 |
| invalid_cvv | 1.00 | 1.00 | 11 | 0 | 0 |
| card_declined_generic | 1.00 | 1.00 | 6 | 0 | 0 |
| unknown | 0.00 | 0.00 | 0 | 0 | 0 |

### Confusion Matrix
| True \ Pred | insufficient_funds | expired_card | network_timeout | bank_server_down | user_abandoned | invalid_cvv | card_declined_generic | unknown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| insufficient_funds | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| expired_card | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| network_timeout | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| bank_server_down | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 |
| user_abandoned | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 |
| invalid_cvv | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 0 |
| card_declined_generic | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Detail Log
| Raw Text | True Category | Predicted Category | Confidence | Mode Used | Correct? | Reasoning |
| --- | --- | --- | --- | --- | --- | --- |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| declined due to low funds | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| read timeout from upstream | network_timeout | network_timeout | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| EXPIRED_CARD | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline: CVV mismatch | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline 51 | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 96 - System Malfunction | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| NSF Decline | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline: card has expired | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| abandoned by customer during auth | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Not enough balance to complete transaction | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| the card has reached its expiration date | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline: CVV mismatch | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 96 System error / bank down | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| bank server is down/offline | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 91 - System Error / Timeout | network_timeout | network_timeout | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| card declined by issuing bank | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| incorrect details | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| connection reset by peer | network_timeout | network_timeout | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline: card has expired | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 05 Generic decline | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| NSF Decline | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Issuer Down | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| upstream service unavailable | network_timeout | network_timeout | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| User navigated back from checkout page | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 05 - Do Not Honor | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| card verification code incorrect | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| session expired on OTP screen | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Issuer Down | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| User navigated back from checkout page | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| card issuer declined this charge | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| customer dropped off | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| canceled by customer | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| account has insufficient funds for payment | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 54 Card expired | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 51 Insufficient funds / over limit | insufficient_funds | insufficient_funds | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| DO_NOT_HONOR | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| decline: bank unavailable | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| remote system failed to respond | bank_server_down | bank_server_down | 0.85 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| 05 Generic decline | card_declined_generic | card_declined_generic | 0.55 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| exipred card info provided | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| read timeout from upstream | network_timeout | network_timeout | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| security code check failed | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| CVC/CVV2 error | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| Incorrect security code | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| customer clicked cancel | user_abandoned | user_abandoned | 0.70 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| card status: expired | expired_card | expired_card | 0.95 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
| INVALID_CVV | invalid_cvv | invalid_cvv | 0.90 | deterministic_fallback | Yes | AI prediction unavailable — deterministic fallback used. |
