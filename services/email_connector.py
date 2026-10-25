import os
import json
import base64
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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
CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "email_config.json"


class EmailConnectorService:
    def __init__(self, worker_url: Optional[str] = None):
        self.worker_url = worker_url or CLOUDFLARE_WORKER_URL
        INCOMING_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_config()

    def _ensure_config(self) -> None:
        if not CONFIG_FILE.exists():
            default_conf = {
                "provider": "sandbox",  # "smtp", "resend", "sandbox"
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": os.environ.get("SMTP_USER", ""),
                "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
                "smtp_use_tls": True,
                "from_email": os.environ.get("SMTP_FROM", "procurement@redliner.ai"),
                "from_name": "RedLiner Enterprise Procurement",
                "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_conf, f, indent=2)

    def get_config(self, mask_secret: bool = True) -> Dict[str, Any]:
        self._ensure_config()
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if mask_secret and cfg.get("smtp_password"):
            cfg["smtp_password_masked"] = "••••••••••••"
            cfg["has_smtp_password"] = True
        else:
            cfg["has_smtp_password"] = bool(cfg.get("smtp_password"))
        if mask_secret and cfg.get("resend_api_key"):
            cfg["resend_api_key_masked"] = cfg["resend_api_key"][:4] + "••••••••"
            cfg["has_resend_api_key"] = True
        else:
            cfg["has_resend_api_key"] = bool(cfg.get("resend_api_key"))
        return cfg

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_config(mask_secret=False)
        # Only overwrite password if a non-masked string is provided
        if "smtp_password" in new_config and new_config["smtp_password"] == "••••••••••••":
            new_config["smtp_password"] = current.get("smtp_password", "")
        if "resend_api_key" in new_config and "••••" in new_config["resend_api_key"]:
            new_config["resend_api_key"] = current.get("resend_api_key", "")

        current.update(new_config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return self.get_config(mask_secret=True)

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
            f"Thank you for sharing the draft agreement for {vendor_name}. Our enterprise legal and procurement teams have completed an initial review against our corporate onboarding playbook.",
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

    def _send_smtp(
        self,
        config: Dict[str, Any],
        recipient_email: str,
        subject: str,
        body_text: str,
        attachment_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Transmits a real email with attachment over standard SMTP (e.g. Gmail App Password, Brevo, AWS SES)."""
        host = config.get("smtp_host", "smtp.gmail.com")
        port = int(config.get("smtp_port", 587))
        user = config.get("smtp_user", "")
        password = config.get("smtp_password", "")
        use_tls = config.get("smtp_use_tls", True)
        from_email = config.get("from_email") or user
        from_name = config.get("from_name", "RedLiner Enterprise Procurement")

        if not user or not password:
            raise ValueError("SMTP credentials missing. Please configure SMTP username and password / App Password.")

        msg = MIMEMultipart("mixed")
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #201515; max-width: 650px; margin: 0 auto; padding: 20px; border: 1px solid #E8E2D9; border-radius: 8px;">
          <div style="border-bottom: 2px solid #FF4F00; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #201515; margin: 0; font-size: 20px;">RedLiner Legal & Procurement Operations</h2>
            <p style="color: #6B635B; margin: 4px 0 0; font-size: 13px;">B2B Autonomous Contract Negotiation</p>
          </div>
          <div style="white-space: pre-wrap; font-size: 14px;">{body_text}</div>
          <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #E8E2D9; font-size: 12px; color: #6B635B;">
            <p>📎 <strong>Attachment:</strong> Native Microsoft Word document with tracked changes and review comments.</p>
            <p>Sent autonomously via <strong>RedLiner Agentic Contracting System</strong>.</p>
          </div>
        </div>
        """

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body_text, "plain", "utf-8"))
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt_part)

        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.wordprocessingml.document")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{attachment_path.name}"')
                msg.attach(part)

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=12.0)
        else:
            server = smtplib.SMTP(host, port, timeout=12.0)
            if use_tls:
                server.starttls()

        server.login(user, password)
        server.sendmail(from_email, [recipient_email], msg.as_string())
        server.quit()

        return {
            "is_real_delivery": True,
            "provider": f"Direct SMTP ({host}:{port})",
            "delivered_to": recipient_email,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attachment": attachment_path.name if attachment_path else None
        }

    def _send_resend(
        self,
        config: Dict[str, Any],
        recipient_email: str,
        subject: str,
        body_text: str,
        attachment_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Transmits a real email using Resend API."""
        api_key = config.get("resend_api_key", "")
        from_email = config.get("from_email", "onboarding@resend.dev")
        from_name = config.get("from_name", "RedLiner Enterprise Procurement")

        if not api_key:
            raise ValueError("Resend API Key missing. Please provide your Resend API Key in Email Settings.")

        attachments = []
        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                attachments.append({
                    "filename": attachment_path.name,
                    "content": b64
                })

        payload = {
            "from": f"{from_name} <{from_email}>",
            "to": [recipient_email],
            "subject": subject,
            "text": body_text,
            "attachments": attachments
        }

        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=10.0
        )
        if resp.status_code not in [200, 201]:
            raise RuntimeError(f"Resend API error: {resp.status_code} {resp.text}")

        return {
            "is_real_delivery": True,
            "provider": "Resend API",
            "delivered_to": recipient_email,
            "resend_response": resp.json()
        }

    def send_test_email(self, target_email: str) -> Dict[str, Any]:
        """Sends a verification email to ensure SMTP / Resend configuration is working."""
        config = self.get_config(mask_secret=False)
        provider = config.get("provider", "sandbox").lower()

        test_subject = "RedLiner Email Dispatcher — System Verification"
        test_body = f"""Hello from RedLiner!

This is an automated test email confirming that your email dispatcher is successfully configured.

Provider Mode: {provider.upper()}
Timestamp: {datetime.now(timezone.utc).isoformat()}
Recipient: {target_email}

Your RedLiner system is ready to autonomously dispatch redlined Word documents and counter-proposals to real counterparties.
"""
        if provider == "smtp":
            return self._send_smtp(config, target_email, test_subject, test_body, None)
        elif provider == "resend":
            return self._send_resend(config, target_email, test_subject, test_body, None)
        else:
            return {
                "is_real_delivery": False,
                "provider": "Simulated Gateway (Sandbox Mode)",
                "note": "Email dispatcher is currently in Sandbox Simulation Mode. Switch to Direct SMTP or Resend to send real emails to your inbox."
            }

    def dispatch_email(
        self,
        outbound_request: OutboundEmailRequest,
        docx_file_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        config = self.get_config(mask_secret=False)
        provider = config.get("provider", "sandbox").lower()

        # If SMTP is configured with user and password, attempt real SMTP delivery
        if provider == "smtp" and config.get("smtp_user") and config.get("smtp_password"):
            try:
                res = self._send_smtp(
                    config=config,
                    recipient_email=outbound_request.recipient_email,
                    subject=outbound_request.subject,
                    body_text=outbound_request.counter_proposal_body,
                    attachment_path=docx_file_path
                )
                log_email_audit(
                    direction="OUTBOUND",
                    source="SMTP_DISPATCH",
                    recipient_or_sender=outbound_request.recipient_email,
                    subject=outbound_request.subject,
                    has_attachment=bool(docx_file_path),
                    attachment_name=outbound_request.redlined_docx_filename,
                    status="SUCCESS",
                    details=res,
                )
                return {
                    "status": "SUCCESS",
                    "is_real_delivery": True,
                    "provider": res["provider"],
                    "recipient": outbound_request.recipient_email,
                    "subject": outbound_request.subject,
                    "deal_reference": outbound_request.deal_reference,
                    "response": res,
                    "message": f"Real email dispatched via SMTP to {outbound_request.recipient_email} with attached Word document."
                }
            except Exception as e:
                err_msg = f"SMTP transmission error: {str(e)}"
                print(f"[EmailConnectorService] {err_msg}")
                log_email_audit(
                    direction="OUTBOUND",
                    source="SMTP_DISPATCH",
                    recipient_or_sender=outbound_request.recipient_email,
                    subject=outbound_request.subject,
                    has_attachment=bool(docx_file_path),
                    attachment_name=outbound_request.redlined_docx_filename,
                    status="SMTP_ERROR",
                    details={"error": str(e)},
                )
                return {
                    "status": "LOCAL_MOCK_DISPATCHED",
                    "is_real_delivery": False,
                    "provider": "SMTP (Failed Handshake)",
                    "error": str(e),
                    "recipient": outbound_request.recipient_email,
                    "subject": outbound_request.subject,
                    "deal_reference": outbound_request.deal_reference,
                    "message": f"SMTP delivery failed ({str(e)}). Please verify your SMTP password / App Password."
                }

        # If Resend is configured
        if provider == "resend" and config.get("resend_api_key"):
            try:
                res = self._send_resend(
                    config=config,
                    recipient_email=outbound_request.recipient_email,
                    subject=outbound_request.subject,
                    body_text=outbound_request.counter_proposal_body,
                    attachment_path=docx_file_path
                )
                log_email_audit(
                    direction="OUTBOUND",
                    source="RESEND_DISPATCH",
                    recipient_or_sender=outbound_request.recipient_email,
                    subject=outbound_request.subject,
                    has_attachment=bool(docx_file_path),
                    attachment_name=outbound_request.redlined_docx_filename,
                    status="SUCCESS",
                    details=res,
                )
                return {
                    "status": "SUCCESS",
                    "is_real_delivery": True,
                    "provider": "Resend API",
                    "recipient": outbound_request.recipient_email,
                    "subject": outbound_request.subject,
                    "deal_reference": outbound_request.deal_reference,
                    "response": res,
                    "message": f"Real email dispatched via Resend to {outbound_request.recipient_email}."
                }
            except Exception as e:
                print(f"[EmailConnectorService] Resend error: {e}")
                return {
                    "status": "LOCAL_MOCK_DISPATCHED",
                    "is_real_delivery": False,
                    "provider": "Resend (Failed)",
                    "error": str(e),
                    "recipient": outbound_request.recipient_email,
                    "subject": outbound_request.subject,
                    "deal_reference": outbound_request.deal_reference,
                    "message": f"Resend delivery failed: {str(e)}"
                }

        # Otherwise Sandbox / Simulated Mode
        sim_response = {
            "is_real_delivery": False,
            "delivery_id": f"sim_sandbox_{int(datetime.now().timestamp())}",
            "provider": "Simulated Gateway (Sandbox Mode)",
            "recipient": outbound_request.recipient_email,
            "attachment": outbound_request.redlined_docx_filename,
            "status": "QUEUED_IN_SANDBOX",
            "guidance": "To deliver real emails across the Internet to this address, enter your SMTP or Resend credentials in Email Settings below."
        }
        log_email_audit(
            direction="OUTBOUND",
            source="SANDBOX_SIMULATION",
            recipient_or_sender=outbound_request.recipient_email,
            subject=outbound_request.subject,
            has_attachment=bool(docx_file_path),
            attachment_name=outbound_request.redlined_docx_filename,
            status="LOCAL_MOCK_DISPATCHED",
            details=sim_response,
        )
        return {
            "status": "LOCAL_MOCK_DISPATCHED",
            "is_real_delivery": False,
            "provider": "Simulated Gateway (Sandbox Mode)",
            "recipient": outbound_request.recipient_email,
            "subject": outbound_request.subject,
            "deal_reference": outbound_request.deal_reference,
            "response": sim_response,
            "message": f"Simulated Delivery (Sandbox Mode): Counter-proposal generated for {outbound_request.recipient_email}. Configure SMTP in Email Settings to deliver real emails to your Gmail inbox."
        }
