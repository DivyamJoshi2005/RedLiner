class PythonMathEngine:
    """Calculates normalized utility score combining pricing models, payment terms, and risk penalties."""

    @staticmethod
    def calculate_utility(
        unit_price: float,
        target_price: float,
        payment_terms_days: int = 60,
        risk_penalty: float = 0.0,
    ) -> float:
        """
        Normalized utility score between 0.0 and 1.0.
        Higher is better for the buyer.
        """
        # Price score (50% weight): 1.0 if at or below target, scales down as price exceeds target
        price_ratio = target_price / max(unit_price, 1.0)
        price_utility = min(1.0, price_ratio) * 0.5

        # Payment term utility (30% weight): Net 60 = 0.3, Net 30 = 0.15, Net 15 = 0.05
        term_utility = (min(payment_terms_days, 60) / 60.0) * 0.3

        # Risk penalty deduction (20% weight)
        risk_deduction = (min(risk_penalty, 100.0) / 100.0) * 0.2

        total_utility = max(0.0, min(1.0, price_utility + term_utility - risk_deduction))
        return round(total_utility, 3)
