from pydantic import BaseModel
from typing import List

class CandidateAction(BaseModel):
    action: str
    probability: float
    confidence: float = 0.95
    reason: str = "Standard prediction choice based on context."

class ActionWithValue(BaseModel):
    action: str
    probability: float
    cost: float
    expected_value: float

def compute_expected_value(
    amount: float,
    candidate_actions: List[CandidateAction],
    action_costs: dict
) -> List[ActionWithValue]:
    """
    Computes Expected Net Recovery for each candidate recovery action.
    Expected Net Recovery = amount * predicted_recovery_probability - action_cost
    """
    valued_actions = []
    for candidate in candidate_actions:
        cost = action_costs.get(candidate.action, 0.0)
        # Expected Net Recovery = (amount * probability) - cost
        expected_val = (amount * candidate.probability) - cost
        valued_actions.append(
            ActionWithValue(
                action=candidate.action,
                probability=candidate.probability,
                cost=cost,
                expected_value=round(expected_val, 2)
            )
        )
    # Sort candidate actions by expected value descending
    valued_actions.sort(key=lambda x: x.expected_value, reverse=True)
    return valued_actions
