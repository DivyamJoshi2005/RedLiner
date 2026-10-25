import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.models import (
    ParsedDocument,
    RedlineResult,
    VendorProfile,
    InboundEmailWebhook,
    OutboundEmailRequest,
)
from agents.orchestrator import MainOrchestrator
from agents.legal_redliner import LegalRedlinerAgent
from agents.vendor_intelligence import VendorIntelligenceAgent
from agents.email_writer import EmailWriterAgent
from subgraphs.document_parser import DocumentParserSubgraph
from subgraphs.human_approval import FeedbackAgent
from Helpers.logger import get_recent_logs

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
OUTPUTS_DIR = BASE_DIR / "data" / "outputs"
SAMPLE_DIR = BASE_DIR / "data" / "sample_contracts"
DASHBOARD_DIR = BASE_DIR / "dashboard"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="RedLiner — B2B Autonomous Contract Negotiation & Redlining",
    description="Agentic contract orchestration with subagents and subgraphs matching the project synopsis architecture.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Supervisor & Specialized Agents / Subgraphs
orchestrator = MainOrchestrator()
doc_parser = DocumentParserSubgraph()
legal_redliner = LegalRedlinerAgent()
vendor_intelligence = VendorIntelligenceAgent()
email_writer = EmailWriterAgent()


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "RedLiner Core Orchestration System",
        "agents": [
            "MainOrchestrator",
            "LegalRedlinerAgent",
            "VendorIntelligenceAgent",
            "EmailWriterAgent",
            "ProcurementNegotiatorAgent",
            "FinanceComplianceRiskAgent"
        ],
        "subgraphs": [
            "DocumentParserSubgraph",
            "PlaybookMatcherSubgraph",
            "VendorInformationSubgraph",
            "TradeoffEngineSubgraph",
            "HumanApprovalSubgraph"
        ],
    }


@app.post("/api/parser/parse")
async def parse_document(file: Optional[UploadFile] = File(None), sample_name: Optional[str] = Form(None)):
    """Executes DocumentParserSubgraph on uploaded .docx/.pdf or sample file."""
    target_path: Optional[Path] = None

    if sample_name:
        sample_path = SAMPLE_DIR / sample_name
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample '{sample_name}' not found.")
        target_path = sample_path
    elif file:
        safe_name = Path(file.filename).name
        target_path = UPLOADS_DIR / safe_name
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    else:
        target_path = SAMPLE_DIR / "vendor_saas_agreement.docx"

    try:
        return doc_parser.execute(target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document parsing error: {str(e)}")


class RedlineRequest(BaseModel):
    filename: str


@app.post("/api/redliner/redline")
def run_redline(req: RedlineRequest):
    """Executes LegalRedlinerAgent and PlaybookMatcherSubgraph to produce native Word tracked changes."""
    source_path = SAMPLE_DIR / req.filename
    if not source_path.exists():
        source_path = UPLOADS_DIR / req.filename
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Contract '{req.filename}' not found.")

    try:
        parsed_doc = doc_parser.execute(source_path)
        output_filename = f"{source_path.stem}_redlined.docx"
        output_path = OUTPUTS_DIR / output_filename

        actual_source = source_path
        if source_path.suffix.lower() == ".pdf":
            import docx
            temp_docx = OUTPUTS_DIR / f"temp_{source_path.stem}.docx"
            doc = docx.Document()
            doc.add_heading(source_path.stem.replace("_", " ").title(), 0)
            for c in parsed_doc.clauses:
                doc.add_heading(c.heading, level=1)
                doc.add_paragraph(c.text)
            doc.save(str(temp_docx))
            actual_source = temp_docx

        redline_result = legal_redliner.generate_redlined_docx(
            source_docx_path=actual_source,
            output_docx_path=output_path,
            clauses=parsed_doc.clauses,
            contract_name=source_path.stem,
        )

        return redline_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redline error: {str(e)}")


@app.get("/api/redliner/download/{filename}")
def download_redlined_file(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        file_path = SAMPLE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/api/vendor/search")
def search_vendors(q: str = "", limit: int = 25):
    """Executes VendorInformationSubgraph search."""
    return vendor_intelligence.search_vendors(q, limit)


@app.get("/api/vendor/assess")
def assess_vendor(name: str):
    """Executes VendorInformationSubgraph multi-factor risk assessment."""
    if not name.strip():
        raise HTTPException(status_code=400, detail="Vendor name or domain is required.")
    return vendor_intelligence.evaluate_counterparty(name)


@app.post("/api/webhook/email")
def inbound_email_webhook(payload: InboundEmailWebhook, auto_process: bool = True):
    """
    Inbound Cloudflare Email Routing Webhook receiver.
    Extracts vendor .docx/.pdf attachments and automatically executes
    the MainOrchestrator pipeline (parsing, vendor screening, playbook redlining, and counter-proposal drafting).
    """
    inbound_res = email_writer.service.process_inbound_webhook(payload)
    saved_attachments = inbound_res.get("saved_attachments", [])

    # If no attachment was sent, check if a sample contract was referenced in subject or default
    if not saved_attachments:
        default_sample = SAMPLE_DIR / "vendor_saas_agreement.docx"
        if default_sample.exists():
            saved_attachments = [str(default_sample)]

    if not auto_process or not saved_attachments:
        return {
            "status": "RECEIVED",
            "inbound_info": inbound_res,
            "message": "Email received without attachments."
        }

    # Automatically process the primary attached contract
    contract_file_path = Path(saved_attachments[0])
    
    # Infer vendor name from sender email domain or sender name
    from_domain = payload.from_email.split("@")[-1] if "@" in payload.from_email else "vendor"
    vendor_query = payload.from_name if payload.from_name and payload.from_name != payload.from_email else from_domain

    deal_id = f"DEAL-EMAIL-{payload.message_id[:12]}"

    deal_state = orchestrator.process_incoming_deal(
        deal_id=deal_id,
        contract_path=contract_file_path,
        vendor_name=vendor_query,
        output_dir=OUTPUTS_DIR,
    )

    return {
        "status": "PROCESSED_AUTOMATICALLY",
        "message_id": payload.message_id,
        "deal_id": deal_id,
        "vendor_screened": deal_state.vendor_profile.company_name if deal_state.vendor_profile else vendor_query,
        "vendor_risk_tier": deal_state.vendor_profile.risk_tier.value if deal_state.vendor_profile else "UNKNOWN",
        "violations_detected": len(deal_state.redline_actions),
        "requires_human_approval": deal_state.requires_human_approval,
        "redlined_docx_filename": deal_state.redline_result.output_docx_filename if deal_state.redline_result else None,
        "counter_proposal_email": deal_state.counter_proposal_email,
        "inbound_info": inbound_res,
    }


class DispatchProposalRequest(BaseModel):
    contract_filename: str
    vendor_name: str
    recipient_email: str
    recipient_name: str


@app.post("/api/email/dispatch-counter-proposal")
def dispatch_counter_proposal(req: DispatchProposalRequest):
    """Executes EmailWriterAgent to dispatch counter-proposal email with native redlined Word document."""
    output_filename = f"{Path(req.contract_filename).stem}_redlined.docx"
    redlined_path = OUTPUTS_DIR / output_filename
    if not redlined_path.exists():
        redlined_path = SAMPLE_DIR / output_filename

    if not redlined_path.exists():
        source_path = SAMPLE_DIR / req.contract_filename
        if not source_path.exists():
            source_path = UPLOADS_DIR / req.contract_filename
        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Source contract '{req.contract_filename}' not found.")
        parsed = doc_parser.execute(source_path)
        redline_result = legal_redliner.generate_redlined_docx(source_path, redlined_path, parsed.clauses)
    else:
        parsed = doc_parser.execute(redlined_path)
        actions = legal_redliner.review_clauses(parsed.clauses)
        redline_result = RedlineResult(
            contract_name=Path(req.contract_filename).stem,
            total_clauses=len(parsed.clauses),
            violations_detected=len(actions),
            critical_count=sum(1 for a in actions if a.severity.value == "CRITICAL"),
            actions=actions,
            output_docx_filename=redlined_path.name,
            output_docx_path=str(redlined_path),
            summary="Existing redline package retrieved.",
        )

    vendor = vendor_intelligence.evaluate_counterparty(req.vendor_name)
    counter_email = email_writer.compose_counter_proposal(
        redline_result=redline_result,
        vendor=vendor,
        recipient_email=req.recipient_email,
        recipient_name=req.recipient_name,
    )

    dispatch_result = email_writer.dispatch_email(counter_email, redlined_path)

    return {
        "status": "DISPATCHED",
        "email_details": counter_email,
        "dispatch_receipt": dispatch_result,
    }


@app.get("/api/helpers/logs")
def get_helpers_logs(log_type: str = "all", limit: int = 50):
    """Reads logs directly from the Helpers directory."""
    return get_recent_logs(log_type, limit)


# Mount static Dashboard
if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
