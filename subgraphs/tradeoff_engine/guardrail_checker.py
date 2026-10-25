class GuardrailChecker:
    """Compares utility score and financial terms with absolute budget caps and minimum utility limits."""

    def __init__(self, budget_cap: float = 150000.0, min_utility_threshold: float = 0.55):
        self.budget_cap = budget_cap
        self.min_utility_threshold = min_utility_threshold

    def is_within_guardrails(self, total_deal_cost: float, utility_score: float) -> bool:
        if total_deal_cost > self.budget_cap:
            return False
        if utility_score < self.min_utility_threshold:
            return False
        return True
