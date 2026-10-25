from pathlib import Path
from typing import Optional, Dict, Any
from core.state import NegotiationDealState
from core.models import RedlineResult
from subgraphs.document_parser import DocumentParserSubgraph
from agents.legal_redliner import LegalRedlinerAgent
from agents.vendor_intelligence import VendorIntelligenceAgent
from agents.email_writer import EmailWriterAgent
from subgraphs.human_approval import SummaryAgent, InterruptionGate


class MainOrchestrator:
    """
    Main Orchestrator / Supervisor Agent (Section 5.1 in PDF Synopsis).
    - First node in the execution graph.
    - Manages state at asynchronous thread checkpoints.
    - Assigns work to specialized subgraphs (DocumentParser, LegalRedliner, VendorIntelligence).
    - Checks deal convergence and triggers Human Approval Gates when thresholds are breached.
    """

    def __init__(self, playbook_path: Optional[Path] = None, worker_url: Optional[str] = None):
        self.doc_parser = DocumentParserSubgraph()
        self.legal_redliner = LegalRedlinerAgent(playbook_path)
        self.vendor_intel = VendorIntelligenceAgent()
        self.email_writer = EmailWriterAgent(worker_url)
        self.summary_agent = SummaryAgent()
        self.interruption_gate = InterruptionGate()

    def reload_playbook(self, new_path: Optional[Path] = None) -> None:
        self.legal_redliner.reload_playbook(new_path)

    def process_incoming_deal(
        self,
        deal_id: str,
        contract_path: Path,
        vendor_name: str,
        output_dir: Path,
        max_iterations: int = 3,
    ) -> NegotiationDealState:
        # Initialize negotiation deal state
        state = NegotiationDealState(
            deal_id=deal_id,
            iteration=1,
            max_iterations=max_iterations,
            source_contract_filename=contract_path.name,
        )

        # 1. Step: Document Parser Subgraph (3.a)
        parsed_doc = self.doc_parser.execute(contract_path)
        state.parsed_clauses = parsed_doc.clauses

        # 2. Step: Parallel dispatch to Vendor Intelligence (3.d)
        vendor_profile = self.vendor_intel.evaluate_counterparty(vendor_name)
        state.vendor_profile = vendor_profile

        # 3. Step: Parallel dispatch to Legal Redliner Subgraph (3.b)
        out_filename = f"{contract_path.stem}_redlined.docx"
        out_docx_path = output_dir / out_filename

        # If input is PDF, create a clean base docx to apply native Word OpenXML tracked changes
        actual_source = contract_path
        if contract_path.suffix.lower() == ".pdf":
            import docx
            temp_docx = output_dir / f"temp_{contract_path.stem}.docx"
            doc = docx.Document()
            doc.add_heading(contract_path.stem.replace("_", " ").title(), 0)
            for c in parsed_doc.clauses:
                doc.add_heading(c.heading, level=1)
                doc.add_paragraph(c.text)
            doc.save(str(temp_docx))
            actual_source = temp_docx

        redline_result: RedlineResult = self.legal_redliner.generate_redlined_docx(
            source_docx_path=actual_source,
            output_docx_path=out_docx_path,
            clauses=state.parsed_clauses,
            contract_name=contract_path.stem,
        )
        state.redline_result = redline_result
        state.redline_actions = redline_result.actions

        # 4. Check Convergence and Human Approval Gate (3.e)
        should_pause = self.interruption_gate.should_interrupt(
            critical_violations=redline_result.critical_count,
            vendor_risk_score=vendor_profile.risk_score
        )
        state.requires_human_approval = should_pause
        state.is_converged = (len(redline_result.actions) == 0)

        # 5. Draft Counter-Proposal Email via Email Writer Agent
        counter_email = self.email_writer.compose_counter_proposal(
            redline_result=redline_result,
            vendor=vendor_profile,
            recipient_email=f"counsel@{vendor_profile.domain}",
            recipient_name=f"{vendor_profile.company_name} Legal Counsel",
        )
        state.counter_proposal_email = counter_email

        return state
