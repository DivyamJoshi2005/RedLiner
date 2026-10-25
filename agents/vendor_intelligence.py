from typing import List
from core.models import VendorProfile
from subgraphs.vendor_information import VendorInformationSubgraph


class VendorIntelligenceAgent:
    """
    Vendor Intelligence Core Agent (Section 5.2.d in PDF Synopsis).
    Conducts due diligence and background checks on counterparties by querying
    corporate registries, sanctions, and credit indicators.
    """

    def __init__(self):
        self.subgraph = VendorInformationSubgraph()

    def search_vendors(self, query: str = "", limit: int = 25) -> List[VendorProfile]:
        return self.subgraph.search(query, limit)

    def evaluate_counterparty(self, vendor_name_or_domain: str) -> VendorProfile:
        return self.subgraph.assess_vendor(vendor_name_or_domain)
