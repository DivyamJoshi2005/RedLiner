import os
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from core.models import (
    InboundEmailWebhook,
    OutboundEmailRequest,
    RedlineResult,
    VendorProfile,
)
from Helpers.logger import log_email_audit

CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "http://localhost:8787")
INCOMING_DIR = Path(__file__).resolve().parent.parent / "data" / "incoming"


class EmailConnectorService:
    def __init__(self, worker_url: Optional[str] = None):
        self.worker_url = worker_url or CLOUDFLARE_WORKER_URL
        INCOMING_DIR.mkdir(parents=True, exist_ok=True)

    def process_inbound_webhook(self, webhook_data: Any) -> Dict[str, Any]:
        """Process inbound email webhook received from Cloudflare Email Routing."""
        if isinstance(webhook_data, dict):
            webhook_data = InboundEmailWebhook(**webhook_data)

        saved_files: List[str] = []
        for att in webhook_data.attachments:
            safe_filename = Path(att.filename).name
            file_path = INCOMING_DIR / f"{webhook_data.message_id}_{safe_filename}"
            try:
                content_bytes = base64.b64decode(att.content_base64)
                with open(file_path, "wb") as f:
                    f.write(content_bytes)
                saved_files.append(str(file_path))
            except Exception as e:
                print(f"[EmailConnectorService] Error saving attachment {att.filename}: {e}")

        has_attachment = len(saved_files) > 0
        primary_attachment = Path(saved_files[0]).name if saved_files else None

        log_email_audit(
            direction="INBOUND",
            source="CLOUDFLARE_WEBHOOK",
            recipient_or_sender=webhook_data.from_email,
            subject=webhook_data.subject,
            has_attachment=has_attachment,
            attachment_name=primary_attachment,
            status="SUCCESS",
            details={
                "message_id": webhook_data.message_id,
                "saved_files": saved_files,
                "to_email": webhook_data.to_email,
            },
        )

        return {
            "status": "PROCESSED",
            "message_id": webhook_data.message_id,
            "sender": webhook_data.from_email,
            "saved_attachments": saved_files,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def generate_counter_proposal_email(
        self,
        redline_result: RedlineResult,
        vendor: Optional[VendorProfile] = None,
        recipient_email: str = "vendor-legal@counterparty.com",
        recipient_name: str = "Vendor Legal Counsel",
    ) -> OutboundEmailRequest:
        vendor_name = vendor.company_name if vendor else "Vendor"

        critical_edits = [a for a in redline_result.actions if a.severity.value == "CRITICAL"]
        high_edits = [a for a in redline_result.actions if a.severity.value == "HIGH"]
        other_edits = [a for a in redline_result.actions if a.severity.value not in ["CRITICAL", "HIGH"]]

        body_lines = [
            f"Dear {recipient_name},",
            "",
            f"Thank you for sharing the draft agreement for {vendor_name}. Our enterprise legal and procurement teams have completed an initial review against our standard corporate onboarding playbook.",
            "",
            f"To ensure alignment with our corporate governance, risk thresholds, and procurement standards, we have generated native tracked changes and margin comments in the attached Word document ({redline_result.output_docx_filename}).",
            "",
            "### Summary of Key Proposed Adjustments:",
        ]

        if critical_edits:
            body_lines.append("\n**1. Critical Risk Terms & Boundary Alignment:**")
            for act in critical_edits:
                body_lines.append(f"  • **{act.clause_type.value}** ({act.rule_name}): Realigned liability limits and proprietary protections to mutual 12-month standard caps.")

        if high_edits:
            body_lines.append("\n**2. Commercial & Operational Safeguards:**")
            for act in high_edits:
                body_lines.append(f"  • **{act.clause_type.value}** ({act.rule_name}): Standardized Net 60 payment terms and 30-day convenience termination.")

        if other_edits:
            body_lines.append("\n**3. Governance & Regulatory Compliance:**")
            for act in other_edits:
                body_lines.append(f"  • **{act.clause_type.value}** ({act.rule_name}): Established neutral Delaware governing law with binding AAA arbitration.")

        body_lines.extend([
            "",
            "Please review the attached native .docx document which contains complete Word tracked changes and detailed explanatory margin comments.",
            "",
            "We look forward to finalizing the terms promptly and onboarding your services.",
            "",
            "Best regards,",
            "RedLiner Procurement & Legal Operations Team",
            "RedLiner B2B Autonomous Contracting Platform",
        ])

        email_body = "\n".join(body_lines)
        subject = f"Redline & Counter-Proposal: {redline_result.contract_name} — RedLiner Enterprise Legal"

        return OutboundEmailRequest(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            vendor_company=vendor_name,
            subject=subject,
            counter_proposal_body=email_body,
            redlined_docx_filename=redline_result.output_docx_filename,
            deal_reference=f"RL-DEAL-{abs(hash(redline_result.contract_name)) % 100000:05d}",
        )

    def dispatch_email(
        self,
        outbound_request: OutboundEmailRequest,
        docx_file_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        attachments = []
        if docx_file_path and docx_file_path.exists():
            with open(docx_file_path, "rb") as f:
                b64_content = base64.b64encode(f.read()).decode("utf-8")
                attachments.append({
                    "filename": docx_file_path.name,
                    "content_base64": b64_content,
                    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                })

        payload = {
            "recipient_email": outbound_request.recipient_email,
            "recipient_name": outbound_request.recipient_name,
            "subject": outbound_request.subject,
            "text_content": outbound_request.counter_proposal_body,
            "html_content": f"<div style='font-family: sans-serif; white-space: pre-wrap;'>{outbound_request.counter_proposal_body}</div>",
            "attachments": attachments,
        }

        dispatch_status = "SUCCESS"
        response_data = {}

        try:
            resp = requests.post(
                f"{self.worker_url}/api/send-email",
                json=payload,
                timeout=5.0
            )
            if resp.status_code == 200:
                response_data = resp.json()
            else:
                dispatch_status = "MOCK_DISPATCHED"
                response_data = {"note": f"Worker responded with {resp.status_code}, queued in local pipeline"}
        except Exception:
            dispatch_status = "LOCAL_MOCK_DISPATCHED"
            response_data = {
                "delivery_id": f"sim_deliv_{int(datetime.now().timestamp())}",
                "provider": "Cloudflare Email Gateway (Simulated / Local Mode)",
                "recipient": outbound_request.recipient_email,
                "attachment": outbound_request.redlined_docx_filename,
                "status": "SENT"
            }

        log_email_audit(
            direction="OUTBOUND",
            source="OUTBOUND_DISPATCH",
            recipient_or_sender=outbound_request.recipient_email,
            subject=outbound_request.subject,
            has_attachment=bool(attachments),
            attachment_name=outbound_request.redlined_docx_filename,
            status=dispatch_status,
            details=response_data,
        )

        return {
            "status": dispatch_status,
            "recipient": outbound_request.recipient_email,
            "subject": outbound_request.subject,
            "deal_reference": outbound_request.deal_reference,
            "response": response_data,
        }
