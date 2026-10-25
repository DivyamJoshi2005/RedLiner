from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.app import app
from subgraphs.document_parser import DocumentParserSubgraph
from subgraphs.playbook_matcher import PlaybookMatcherSubgraph, WordModifier
from subgraphs.vendor_information import VendorInformationSubgraph
from subgraphs.tradeoff_engine import TradeoffEngineSubgraph, PythonMathEngine
from subgraphs.human_approval import InterruptionGate, FeedbackAgent
from agents import (
    MainOrchestrator,
    LegalRedlinerAgent,
    VendorIntelligenceAgent,
    EmailWriterAgent,
    ProcurementNegotiatorAgent,
    FinanceComplianceRiskAgent,
)
from core.models import SanctionStatus, RiskTier, ClauseType

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DOCX = BASE_DIR / "data" / "sample_contracts" / "vendor_saas_agreement.docx"
SAMPLE_PDF = BASE_DIR / "data" / "sample_contracts" / "vendor_saas_agreement.pdf"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"


def test_health_check_architecture():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "MainOrchestrator" in data["agents"]
    assert "DocumentParserSubgraph" in data["subgraphs"]
    assert "PlaybookMatcherSubgraph" in data["subgraphs"]
    assert "VendorInformationSubgraph" in data["subgraphs"]


def test_subgraph_document_parser():
    parser_subgraph = DocumentParserSubgraph()

    # DOCX execution
    parsed_docx = parser_subgraph.execute(SAMPLE_DOCX)
    assert parsed_docx.file_type == "docx"
    assert len(parsed_docx.clauses) >= 7

    clause_types = [c.clause_type for c in parsed_docx.clauses]
    assert ClauseType.LIABILITY_CAP in clause_types
    assert ClauseType.PAYMENT_TERMS in clause_types
    assert ClauseType.IP_RIGHTS in clause_types

    # PDF execution
    parsed_pdf = parser_subgraph.execute(SAMPLE_PDF)
    assert parsed_pdf.file_type == "pdf"
    assert len(parsed_pdf.clauses) >= 7


def test_subgraph_playbook_matcher_and_parallel_checks():
    parser = DocumentParserSubgraph()
    parsed = parser.execute(SAMPLE_DOCX)

    matcher_subgraph = PlaybookMatcherSubgraph()
    actions = matcher_subgraph.match_clauses(parsed.clauses)
    assert len(actions) >= 5

    critical = [a for a in actions if a.severity.value == "CRITICAL"]
    assert len(critical) >= 2

    # Verify native Word OpenXML modification
    out_file = OUTPUT_DIR / "test_subgraph_redlined.docx"
    result = matcher_subgraph.execute(SAMPLE_DOCX, out_file, parsed.clauses)
    assert out_file.exists()
    assert result.violations_detected == len(actions)


def test_subgraph_vendor_information():
    vendor_subgraph = VendorInformationSubgraph()

    # Low risk vendor
    apex = vendor_subgraph.assess_vendor("ApexCloud Enterprise Ltd")
    assert apex.risk_tier == RiskTier.LOW
    assert apex.sanction_pep_status == SanctionStatus.CLEARED

    # OFAC Sanctioned entity
    severo = vendor_subgraph.assess_vendor("SeveroExport Logistics")
    assert severo.risk_tier == RiskTier.CRITICAL
    assert severo.risk_score == 100.0
    assert severo.sanction_pep_status == SanctionStatus.BLOCKED

    # OSINT synthesis for unknown entity
    unknown = vendor_subgraph.assess_vendor("DynamicGlobal Cyber Corp")
    assert unknown.risk_score > 0
    assert "OSINT Notice" in unknown.flags[-1]


def test_subgraph_tradeoff_engine():
    tradeoff = TradeoffEngineSubgraph()
    result = tradeoff.execute(offered_price=120.0, target_price=100.0, vendor_risk_score=15.0)
    assert result["proposed_price"] == 105.0
    assert result["proposed_terms"] == "Net 60"
    assert 0.0 <= result["normalized_utility_score"] <= 1.0
    assert "passed_guardrails" in result


def test_subgraph_human_approval():
    # Critical violations should trigger interruption gate
    should_pause = InterruptionGate.should_interrupt(critical_violations=2, vendor_risk_score=10.0)
    assert should_pause is True

    # High vendor risk should trigger interruption gate
    should_pause_risk = InterruptionGate.should_interrupt(critical_violations=0, vendor_risk_score=85.0)
    assert should_pause_risk is True

    # Feedback agent decisions
    app_dec = FeedbackAgent.process_decision("APPROVE")
    assert app_dec["can_dispatch"] is True

    rej_dec = FeedbackAgent.process_decision("REJECT", "Exceeds liability limits")
    assert rej_dec["can_dispatch"] is False
    assert rej_dec["needs_renegotiation"] is True


def test_core_agents():
    # Procurement negotiator
    procurement = ProcurementNegotiatorAgent()
    concession = procurement.plan_concession(offered_price=100.0)
    assert concession["target_price"] == 90.0

    # Finance compliance risk agent
    finance = FinanceComplianceRiskAgent()
    eval_res = finance.evaluate_boundaries(deal_cost=50000.0, target_cost=45000.0, payment_term_days=60)
    assert eval_res["is_approved"] is True
    assert eval_res["payment_terms_approved"] is True

    # Email writer agent
    email_writer = EmailWriterAgent()
    parser = DocumentParserSubgraph()
    parsed = parser.execute(SAMPLE_DOCX)
    matcher = PlaybookMatcherSubgraph()
    out_docx = OUTPUT_DIR / "agent_test_redlined.docx"
    redline_res = matcher.execute(SAMPLE_DOCX, out_docx, parsed.clauses)

    counter_email = email_writer.compose_counter_proposal(redline_res)
    assert "Redline & Counter-Proposal" in counter_email.subject
    dispatch_res = email_writer.dispatch_email(counter_email, out_docx)
    assert dispatch_res["status"] in ["SUCCESS", "LOCAL_MOCK_DISPATCHED", "MOCK_DISPATCHED"]


def test_main_orchestrator_supervisory_flow():
    orchestrator = MainOrchestrator()
    state = orchestrator.process_incoming_deal(
        deal_id="DEAL-2026-TEST",
        contract_path=SAMPLE_DOCX,
        vendor_name="ApexCloud Enterprise Ltd",
        output_dir=OUTPUT_DIR,
    )

    assert state.deal_id == "DEAL-2026-TEST"
    assert len(state.parsed_clauses) >= 7
    assert state.vendor_profile is not None
    assert state.redline_result is not None
    assert len(state.redline_actions) >= 5
    assert state.counter_proposal_email is not None
    # Because there are critical redlines in the sample, human approval must be triggered
    assert state.requires_human_approval is True


def test_api_endpoints():
    # 1. Parse API
    resp = client.post("/api/parser/parse", data={"sample_name": "vendor_saas_agreement.docx"})
    assert resp.status_code == 200
    assert len(resp.json()["clauses"]) >= 7

    # 2. Redline API
    resp_red = client.post("/api/redliner/redline", json={"filename": "vendor_saas_agreement.docx"})
    assert resp_red.status_code == 200
    assert resp_red.json()["violations_detected"] >= 5

    # 3. Vendor Search API
    resp_v = client.get("/api/vendor/search?q=snowflake")
    assert resp_v.status_code == 200
    assert len(resp_v.json()) >= 1

    # 4. Outbound email dispatch API
    resp_email = client.post("/api/email/dispatch-counter-proposal", json={
        "contract_filename": "vendor_saas_agreement.docx",
        "vendor_name": "ApexCloud Enterprise Ltd",
        "recipient_email": "legal@apexcloud.io",
        "recipient_name": "ApexCloud Legal Counsel"
    })
    assert resp_email.status_code == 200
    assert resp_email.json()["status"] == "DISPATCHED"

    # 5. Helpers logs API
    resp_logs = client.get("/api/helpers/logs?limit=5")
    assert resp_logs.status_code == 200
    assert len(resp_logs.json()) > 0


def test_helpers_folder_integrity():
    helpers_dir = BASE_DIR / "Helpers"
    assert (helpers_dir / "parser_metadata.jsonl").exists()
    assert (helpers_dir / "redline_audit.jsonl").exists()
    assert (helpers_dir / "email_audit.jsonl").exists()
    assert (helpers_dir / "vendor_risk_audit.jsonl").exists()
