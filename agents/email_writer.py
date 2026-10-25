from typing import Optional, Dict, Any
from pathlib import Path
from core.models import RedlineResult, VendorProfile, OutboundEmailRequest
from services.email_connector import EmailConnectorService


class EmailWriterAgent:
    """
    Email Writer Core Agent (Section 5.2.e in PDF Synopsis).
    Combines negotiation decisions, contract context, and justifications
    into professional emails for the vendor counterparty.
    """

    def __init__(self, worker_url: Optional[str] = None):
        self.service = EmailConnectorService(worker_url)

    def compose_counter_proposal(
        self,
        redline_result: RedlineResult,
        vendor: Optional[VendorProfile] = None,
        recipient_email: str = "vendor-legal@counterparty.com",
        recipient_name: str = "Vendor Legal Counsel",
    ) -> OutboundEmailRequest:
        return self.service.generate_counter_proposal_email(
            redline_result=redline_result,
            vendor=vendor,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
        )

    def dispatch_email(
        self,
        request: OutboundEmailRequest,
        redlined_docx_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        return self.service.dispatch_email(request, redlined_docx_path)
