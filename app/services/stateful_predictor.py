from typing import List
from app.services.recovery_context import RecoveryContext
from app.services.recovery_value import CandidateAction

class StatefulPredictor:
    def predict_candidates(self, transaction, context: RecoveryContext) -> List[CandidateAction]:
        """
        Determines recovery action candidates and calculates probabilities based on transaction and context.
        Implements probability degradation for previously failed actions.
        """
        # Baseline probability map
        base_probs = {
            "retry_payment": 0.50,
            "retry_after_delay": 0.55,
            "request_new_payment_method": 0.65,
            "send_recovery_message": 0.35,
            "escalate_human": 0.20,
            "no_action": 0.0
        }
        
        # Build candidates
        candidates = []
        for action, prob in base_probs.items():
            current_prob = prob
            confidence = 0.95  # Mock confidence for deterministic, but isolated semantic
            reason = f"Baseline prediction for {action}."
            
            # Apply degradation if action failed previously
            if action in context.actions_failed:
                # Degrade probability by 90%
                current_prob = prob * 0.10
                reason = f"Probability degraded for {action} due to previous failed attempt."
            
            candidates.append(
                CandidateAction(
                    action=action,
                    probability=current_prob,
                    confidence=confidence,
                    reason=reason
                )
            )
            
        return candidates
