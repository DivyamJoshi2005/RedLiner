from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.models import Clause, RedlineAction, VendorProfile, RedlineResult, OutboundEmailRequest


class NegotiationDealState(BaseModel):
    """
    Master state schema for the cyclic LangGraph workflow described in the PDF Synopsis.
    Main Orchestrator manages this state at asynchronous thread checkpoints.
    """
    deal_id: str
    iteration: int = 1
    max_iterations: int = 5
    is_converged: bool = False
    requires_human_approval: bool = False
    human_decision: Optional[str] = None  # "APPROVE", "REJECT", "MANUAL_EDIT"

    # Document details
    source_contract_filename: str
    parsed_clauses: List[Clause] = Field(default_factory=list)

    # Redlining & Risk
    redline_actions: List[RedlineAction] = Field(default_factory=list)
    redline_result: Optional[RedlineResult] = None
    vendor_profile: Optional[VendorProfile] = None

    # Tradeoffs & Financials (PDF Subgraph 3.c)
    target_price: Optional[float] = None
    offered_price: Optional[float] = None
    target_payment_terms: str = "Net 60"
    normalized_utility_score: float = 0.0

    # Outbound counter-proposal email
    counter_proposal_email: Optional[OutboundEmailRequest] = None
    audit_logs: List[Dict[str, Any]] = Field(default_factory=list)
