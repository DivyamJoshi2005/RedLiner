import re
from typing import List, Tuple
from core.models import SanctionStatus, RiskTier


class ScoreAggregator:
    """Combines external indicators into a standardized multi-factor score (0-100)."""

    @staticmethod
    def calculate_score(
        credit_score: int,
        financial_rating: str,
        sanction_status: SanctionStatus,
        past_litigation_count: int,
        domain_age_years: float,
        domain: str,
        certifications: List[str]
    ) -> Tuple[float, RiskTier, List[str]]:
        flags: List[str] = []

        if sanction_status == SanctionStatus.BLOCKED:
            flags.append("CRITICAL: Counterparty matched on OFAC / SDN / International Sanctions List. Transaction blocked.")
            return 100.0, RiskTier.CRITICAL, flags

        score = 0.0

        if sanction_status == SanctionStatus.FLAGGED:
            score += 45.0
            flags.append("HIGH: Active PEP (Politically Exposed Person) or secondary sanctions review inquiry.")

        credit_risk = max(0.0, (100.0 - credit_score) * 0.3)
        score += credit_risk

        rating_penalties = {
            "AAA": 0.0,
            "AA": 2.0,
            "A": 4.0,
            "BBB": 8.0,
            "BB": 14.0,
            "B": 20.0,
            "CCC": 26.0,
            "D": 32.0,
        }
        score += rating_penalties.get(financial_rating.upper(), 10.0)

        if credit_score < 50:
            flags.append(f"Financial Warning: Low credit score ({credit_score}/100) indicates elevated insolvency risk.")

        if past_litigation_count >= 3:
            score += 18.0
            flags.append(f"Legal Warning: Elevated dispute record with {past_litigation_count} active/past commercial lawsuits.")
        elif past_litigation_count >= 1:
            score += 6.0

        if domain_age_years < 1.0:
            score += 18.0
            flags.append(f"Domain Warning: Newly registered domain ({domain_age_years:.1f} years). Higher risk of shell entity.")
        elif domain_age_years < 3.0:
            score += 7.0

        if re.search(r"\.(su|biz|cc|ru|top|xyz)$", domain.lower()):
            score += 10.0
            flags.append(f"TLD Notice: Domain uses high-risk or offshore suffix ({domain}).")

        has_soc2 = any("soc 2" in c.lower() for c in certifications)
        has_iso = any("iso 27001" in c.lower() for c in certifications)
        has_gdpr = any("gdpr" in c.lower() for c in certifications)

        if has_soc2:
            score -= 10.0
        if has_iso:
            score -= 8.0
        if has_gdpr:
            score -= 4.0

        if not certifications:
            score += 15.0
            flags.append("Security Warning: No enterprise compliance certifications (SOC 2 or ISO 27001) verified.")

        final_score = max(0.0, min(100.0, round(score, 1)))

        if final_score >= 75.0:
            tier = RiskTier.CRITICAL
        elif final_score >= 50.0:
            tier = RiskTier.HIGH
        elif final_score >= 25.0:
            tier = RiskTier.MEDIUM
        else:
            tier = RiskTier.LOW

        return final_score, tier, flags
