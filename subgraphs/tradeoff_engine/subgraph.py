from .tradeoff_generator import TradeoffGenerator
from .math_engine import PythonMathEngine
from .guardrail_checker import GuardrailChecker


class TradeoffEngineSubgraph:
    """Tradeoff Engine Subgraph (Section 5.3.c in PDF Synopsis)."""

    def __init__(self):
        self.generator = TradeoffGenerator()
        self.math_engine = PythonMathEngine()
        self.guardrail_checker = GuardrailChecker()

    def execute(self, offered_price: float, target_price: float, vendor_risk_score: float = 0.0):
        return self.generator.generate_counter_proposal(offered_price, target_price, 30, vendor_risk_score)
