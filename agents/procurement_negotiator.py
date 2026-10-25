from typing import Dict, Any


class ProcurementNegotiatorAgent:
    """
    Procurement Negotiator Core Agent (Section 5.2.a in PDF Synopsis).
    Reviews unit pricing, volume discounts, and service-level agreements (SLAs).
    Sets target prices and plans concessions.
    """

    def __init__(self, target_discount_pct: float = 10.0):
        self.target_discount_pct = target_discount_pct

    def plan_concession(self, offered_price: float) -> Dict[str, Any]:
        target_price = offered_price * (1.0 - (self.target_discount_pct / 100.0))
        return {
            "offered_price": offered_price,
            "target_price": round(target_price, 2),
            "planned_discount_pct": self.target_discount_pct,
            "negotiation_target": "5% concession on pricing in exchange for Net 60 payment terms"
        }
