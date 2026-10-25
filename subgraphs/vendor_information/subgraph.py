from typing import List, Optional
from core.models import VendorProfile
from Helpers.logger import log_vendor_risk_audit
from .osint_collectors import OSINTCollector
from .score_aggregator import ScoreAggregator


class VendorInformationSubgraph:
    """
    Vendor Information Subgraph (Section 5.3.d in PDF Synopsis).
    Checks counterparties and screens for sanctions.
    Parallel OSINT Collectors query corporate registry records, sanctions, domain age, and credit indicators.
    Exception Handler manages timeouts and retries.
    Score Aggregator combines external data into standardized scores.
    """

    def __init__(self):
        self.collector = OSINTCollector()
        self.aggregator = ScoreAggregator()

    def search(self, query: str = "", limit: int = 25) -> List[VendorProfile]:
        return self.collector.query_registry_and_sanctions(query, limit)

    def assess_vendor(self, vendor_name_or_domain: str) -> VendorProfile:
        matches = self.search(vendor_name_or_domain, limit=1)
        if matches:
            profile = matches[0]
        else:
            profile = self.collector.synthesize_live_osint(vendor_name_or_domain)

        log_vendor_risk_audit(
            vendor_name=profile.company_name,
            domain=profile.domain,
            risk_score=profile.risk_score,
            risk_tier=profile.risk_tier.value,
            sanction_status=profile.sanction_pep_status.value,
            credit_rating=profile.financial_rating,
            flags=profile.flags,
        )

        return profile
