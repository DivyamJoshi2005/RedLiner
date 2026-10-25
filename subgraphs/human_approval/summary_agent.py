from typing import List, Dict, Any, Optional
from core.models import RedlineAction, VendorProfile


class SummaryAgent:
    """Summarizes proposed redlines, financial trade-offs, and risk scores in plain English (PDF 5.3.e)."""

    @staticmethod
    def generate_deal_summary(
        contract_name: str,
        actions: List[RedlineAction],
        vendor_profile: Optional[VendorProfile] = None,
        utility_score: float = 0.0,
    ) -> Dict[str, Any]:
        critical_count = sum(1 for a in actions if a.severity.value == "CRITICAL")
        high_count = sum(1 for a in actions if a.severity.value == "HIGH")

        vendor_risk_tier = vendor_profile.risk_tier.value if vendor_profile else "UNKNOWN"
        vendor_score = vendor_profile.risk_score if vendor_profile else 0.0

        plain_english = (
            f"Deal Review for '{contract_name}': {len(actions)} contract term revisions proposed "
            f"({critical_count} critical, {high_count} operational). "
            f"Counterparty risk tier is evaluated as {vendor_risk_tier} ({vendor_score}/100). "
            f"Overall negotiation utility score is {utility_score:.2f}."
        )

        return {
            "headline": f"{contract_name} Negotiation Summary",
            "summary_text": plain_english,
            "critical_violations": critical_count,
            "total_redlines": len(actions),
            "vendor_risk_tier": vendor_risk_tier,
            "requires_cfo_signoff": critical_count > 0 or vendor_risk_tier in ["HIGH", "CRITICAL"],
        }
