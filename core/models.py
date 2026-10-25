from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    LIABILITY_CAP = "LIABILITY_CAP"
    INDEMNIFICATION = "INDEMNIFICATION"
    IP_RIGHTS = "IP_RIGHTS"
    GOVERNING_LAW = "GOVERNING_LAW"
    PAYMENT_TERMS = "PAYMENT_TERMS"
    TERMINATION = "TERMINATION"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    WARRANTIES_REPRESENTATIONS = "WARRANTIES_REPRESENTATIONS"
    DATA_PRIVACY_SECURITY = "DATA_PRIVACY_SECURITY"
    NON_SOLICITATION = "NON_SOLICITATION"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    MISCELLANEOUS = "MISCELLANEOUS"


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    REPLACE = "REPLACE"
    DELETE = "DELETE"
    INSERT = "INSERT"


class Clause(BaseModel):
    id: str
    clause_type: ClauseType
    heading: str
    text: str
    paragraph_index: int
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    original_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    filename: str
    file_type: str  # docx or pdf
    total_paragraphs: int
    clauses: List[Clause]
    clause_distribution: Dict[str, int]
    raw_text: Optional[str] = None


class PlaybookRule(BaseModel):
    id: str
    name: str
    target_clause_type: ClauseType
    severity: SeverityLevel
    pattern_triggers: List[str] = Field(default_factory=list)
    forbidden_terms: List[str] = Field(default_factory=list)
    required_terms: List[str] = Field(default_factory=list)
    preferred_fallback_text: str
    comment_explanation: str
    guidance_note: Optional[str] = None


class RedlineAction(BaseModel):
    action_id: str
    clause_id: str
    clause_type: ClauseType
    action_type: ActionType
    target_paragraph_index: int
    original_text: str
    replacement_text: str
    comment: str
    rule_id: str
    rule_name: str
    severity: SeverityLevel


class RedlineResult(BaseModel):
    contract_name: str
    total_clauses: int
    violations_detected: int
    critical_count: int
    actions: List[RedlineAction]
    output_docx_filename: str
    output_docx_path: str
    summary: str


class SanctionStatus(str, Enum):
    CLEARED = "CLEARED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VendorProfile(BaseModel):
    vendor_id: str
    company_name: str
    domain: str
    country: str
    registration_number: str
    domain_age_years: float
    credit_score: int
    financial_rating: str
    sanction_pep_status: SanctionStatus
    past_litigation_count: int
    compliance_certifications: List[str] = Field(default_factory=list)
    annual_revenue_usd_m: Optional[float] = None
    employee_count: Optional[int] = None
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_tier: RiskTier = RiskTier.LOW
    flags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class EmailAttachment(BaseModel):
    filename: str
    content_base64: str
    content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class InboundEmailWebhook(BaseModel):
    message_id: str
    from_email: str
    from_name: Optional[str] = ""
    to_email: str
    subject: str
    text_content: Optional[str] = ""
    html_content: Optional[str] = ""
    attachments: List[EmailAttachment] = Field(default_factory=list)


class OutboundEmailRequest(BaseModel):
    recipient_email: str
    recipient_name: str
    vendor_company: str
    subject: str
    counter_proposal_body: str
    redlined_docx_filename: str
    deal_reference: Optional[str] = "REDLINER-MSA-001"
