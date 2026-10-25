import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

HELPERS_DIR = Path(__file__).resolve().parent

PARSER_LOG_FILE = HELPERS_DIR / "parser_metadata.jsonl"
REDLINE_LOG_FILE = HELPERS_DIR / "redline_audit.jsonl"
EMAIL_LOG_FILE = HELPERS_DIR / "email_audit.jsonl"
VENDOR_LOG_FILE = HELPERS_DIR / "vendor_risk_audit.jsonl"
ACTIVITY_LOG_FILE = HELPERS_DIR / "activity_log.jsonl"


def _append_jsonl(filepath: Path, data: Dict[str, Any]) -> None:
    """Safely append a timestamped JSON line to the target log file."""
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        print(f"[Helpers.logger] Error writing to {filepath}: {e}")


def log_parser_metadata(
    filename: str,
    file_type: str,
    paragraphs_count: int,
    clauses_identified: int,
    clause_types_found: List[str],
    elapsed_ms: float,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    data = {
        "event": "DOCUMENT_PARSED",
        "filename": filename,
        "file_type": file_type,
        "paragraphs_count": paragraphs_count,
        "clauses_identified": clauses_identified,
        "clause_types_found": clause_types_found,
        "elapsed_ms": round(elapsed_ms, 2),
        "extra": extra or {},
    }
    _append_jsonl(PARSER_LOG_FILE, data)
    _append_jsonl(ACTIVITY_LOG_FILE, {"type": "parser", **data})


def log_redline_audit(
    contract_name: str,
    playbook_used: str,
    total_clauses: int,
    violations_detected: int,
    critical_violations: int,
    actions_generated: int,
    output_docx_path: str,
    actions_summary: List[Dict[str, Any]],
) -> None:
    data = {
        "event": "REDLINE_EXECUTED",
        "contract_name": contract_name,
        "playbook_used": playbook_used,
        "total_clauses": total_clauses,
        "violations_detected": violations_detected,
        "critical_violations": critical_violations,
        "actions_generated": actions_generated,
        "output_docx_path": output_docx_path,
        "actions_summary": actions_summary,
    }
    _append_jsonl(REDLINE_LOG_FILE, data)
    _append_jsonl(ACTIVITY_LOG_FILE, {"type": "redline", **data})


def log_email_audit(
    direction: str,  # INBOUND or OUTBOUND
    source: str,     # CLOUDFLARE_WEBHOOK or OUTBOUND_DISPATCH
    recipient_or_sender: str,
    subject: str,
    has_attachment: bool,
    attachment_name: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    data = {
        "event": f"EMAIL_{direction}",
        "direction": direction,
        "source": source,
        "party": recipient_or_sender,
        "subject": subject,
        "has_attachment": has_attachment,
        "attachment_name": attachment_name,
        "status": status,
        "details": details or {},
    }
    _append_jsonl(EMAIL_LOG_FILE, data)
    _append_jsonl(ACTIVITY_LOG_FILE, {"type": "email", **data})


def log_vendor_risk_audit(
    vendor_name: str,
    domain: str,
    risk_score: float,
    risk_tier: str,
    sanction_status: str,
    credit_rating: str,
    flags: List[str],
) -> None:
    data = {
        "event": "VENDOR_RISK_ASSESSED",
        "vendor_name": vendor_name,
        "domain": domain,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "sanction_status": sanction_status,
        "credit_rating": credit_rating,
        "flags": flags,
    }
    _append_jsonl(VENDOR_LOG_FILE, data)
    _append_jsonl(ACTIVITY_LOG_FILE, {"type": "vendor_risk", **data})


def get_recent_logs(log_type: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent records from Helpers log files."""
    mapping = {
        "parser": PARSER_LOG_FILE,
        "redline": REDLINE_LOG_FILE,
        "email": EMAIL_LOG_FILE,
        "vendor": VENDOR_LOG_FILE,
        "all": ACTIVITY_LOG_FILE,
    }
    target = mapping.get(log_type, ACTIVITY_LOG_FILE)
    if not target.exists():
        return []

    lines: List[str] = []
    with open(target, "r", encoding="utf-8") as f:
        lines = f.readlines()

    results: List[Dict[str, Any]] = []
    for line in reversed(lines[-limit:]):
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except Exception:
                pass
    return results
