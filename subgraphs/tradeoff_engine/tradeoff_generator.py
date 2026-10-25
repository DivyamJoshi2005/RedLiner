from typing import Dict, Any
from .math_engine import PythonMathEngine
from .guardrail_checker import GuardrailChecker


class TradeoffGenerator:
    """Proposes counter-offers balancing pricing concessions with payment terms."""

    def __init__(self):
        self.math_engine = PythonMathEngine()
        self.guardrail_checker = GuardrailChecker()

    def generate_counter_proposal(
        self,
        offered_price: float,
        target_price: float,
        offered_terms_days: int = 30,
        vendor_risk_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Proposes a balanced tradeoff (e.g., 5% price adjustment for moving Net 30 to Net 60)."""
        proposed_terms = 60
        concession_price = target_price * 1.05 if offered_price > target_price else target_price

        utility = self.math_engine.calculate_utility(
            unit_price=concession_price,
            target_price=target_price,
            payment_terms_days=proposed_terms,
            risk_penalty=vendor_risk_score
        )

        within_limits = self.guardrail_checker.is_within_guardrails(concession_price, utility)

        return {
            "proposed_price": concession_price,
            "proposed_terms": f"Net {proposed_terms}",
            "normalized_utility_score": utility,
            "passed_guardrails": within_limits,
            "tradeoff_rationale": f"Conceded 5% on unit price in exchange for standard Net {proposed_terms} cashflow protection."
        }
