from typing import Dict, Any
from subgraphs.tradeoff_engine import PythonMathEngine, GuardrailChecker


class FinanceComplianceRiskAgent:
    """
    Finance, Compliance & Risk Core Agent (Section 5.2.c in PDF Synopsis).
    The boundary checker. Evaluates financial penalties, payment terms (Net 30 vs Net 60),
    and regulatory risk scores against hard corporate limits.
    """

    def __init__(self, budget_cap: float = 200000.0, min_acceptable_utility: float = 0.5):
        self.math_engine = PythonMathEngine()
        self.guardrail_checker = GuardrailChecker(budget_cap, min_acceptable_utility)

    def evaluate_boundaries(
        self,
        deal_cost: float,
        target_cost: float,
        payment_term_days: int = 60,
        regulatory_risk_score: float = 0.0,
    ) -> Dict[str, Any]:
        utility = self.math_engine.calculate_utility(
            unit_price=deal_cost,
            target_price=target_cost,
            payment_terms_days=payment_term_days,
            risk_penalty=regulatory_risk_score
        )

        within_limits = self.guardrail_checker.is_within_guardrails(deal_cost, utility)

        hard_stop_reasons = []
        if deal_cost > self.guardrail_checker.budget_cap:
            hard_stop_reasons.append(f"Deal cost ${deal_cost:,.2f} exceeds hard budget cap of ${self.guardrail_checker.budget_cap:,.2f}")
        if utility < self.guardrail_checker.min_utility_threshold:
            hard_stop_reasons.append(f"Utility score {utility} below threshold {self.guardrail_checker.min_utility_threshold}")

        return {
            "is_approved": within_limits,
            "utility_score": utility,
            "hard_stop_flags": hard_stop_reasons,
            "regulatory_risk": regulatory_risk_score,
            "payment_terms_approved": payment_term_days >= 45,
        }
