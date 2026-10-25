from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from core.models import PlaybookRule, ClauseType, SeverityLevel

DEFAULT_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "playbooks" / "enterprise_playbook.yaml"
BACKUP_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "playbooks" / "enterprise_playbook.backup.yaml"


def normalize_clause_type(val: Any) -> ClauseType:
    if isinstance(val, ClauseType):
        return val
    raw = str(val or "").strip().upper().replace(" ", "_").replace("-", "_")
    for ct in ClauseType:
        if ct.value == raw:
            return ct
    if "LIAB" in raw:
        return ClauseType.LIABILITY_CAP
    if "INDEM" in raw:
        return ClauseType.INDEMNIFICATION
    if "IP" in raw or "INTELLECTUAL" in raw:
        return ClauseType.IP_RIGHTS
    if "LAW" in raw or "GOVERN" in raw or "JURISDICTION" in raw:
        return ClauseType.GOVERNING_LAW
    if "PAY" in raw or "FEE" in raw or "INVOICE" in raw:
        return ClauseType.PAYMENT_TERMS
    if "TERM" in raw or "CANCEL" in raw:
        return ClauseType.TERMINATION
    if "CONFID" in raw or "NDA" in raw:
        return ClauseType.CONFIDENTIALITY
    if "PRIV" in raw or "DATA" in raw or "SECURITY" in raw:
        return ClauseType.DATA_PRIVACY_SECURITY
    if "WARR" in raw or "REP" in raw:
        return ClauseType.WARRANTIES_REPRESENTATIONS
    if "SOLICIT" in raw:
        return ClauseType.NON_SOLICITATION
    if "FORCE" in raw or "MAJEURE" in raw:
        return ClauseType.FORCE_MAJEURE
    return ClauseType.MISCELLANEOUS


def normalize_severity(val: Any) -> SeverityLevel:
    if isinstance(val, SeverityLevel):
        return val
    raw = str(val or "").strip().upper()
    for sl in SeverityLevel:
        if sl.value == raw:
            return sl
    if "CRIT" in raw or "BLOCK" in raw or "FATAL" in raw:
        return SeverityLevel.CRITICAL
    if "HIGH" in raw:
        return SeverityLevel.HIGH
    if "LOW" in raw or "INFO" in raw:
        return SeverityLevel.LOW
    return SeverityLevel.MEDIUM


class PolicyComparator:
    """Loads active corporate policies and compares structured clauses against playbook rules."""

    def __init__(self, playbook_path: Optional[Path] = None):
        self.playbook_path = playbook_path or DEFAULT_PLAYBOOK_PATH
        self.rules: List[PlaybookRule] = []
        self.playbook_name: str = "Enterprise Corporate Legal Playbook"
        self.version: str = "2026.1"
        self.description: str = "Standard procurement & legal guardrails"
        self.author: str = "RedLiner General Counsel"
        self._ensure_backup()
        self.load_playbook()

    def _ensure_backup(self) -> None:
        if self.playbook_path.exists() and not BACKUP_PLAYBOOK_PATH.exists():
            with open(self.playbook_path, "r", encoding="utf-8") as src, open(BACKUP_PLAYBOOK_PATH, "w", encoding="utf-8") as dst:
                dst.write(src.read())

    def load_playbook(self) -> None:
        if not self.playbook_path.exists():
            if BACKUP_PLAYBOOK_PATH.exists():
                with open(BACKUP_PLAYBOOK_PATH, "r", encoding="utf-8") as src, open(self.playbook_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            else:
                raise FileNotFoundError(f"Playbook file not found at {self.playbook_path}")

        with open(self.playbook_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.playbook_name = data.get("name", "Enterprise Corporate Legal Playbook")
        self.version = str(data.get("version", "2026.1"))
        self.description = data.get("description", "Corporate procurement & legal guardrails")
        self.author = data.get("author", "RedLiner General Counsel")
        raw_rules = data.get("rules", [])

        self.rules = []
        for i, r in enumerate(raw_rules):
            try:
                rule_id = str(r.get("id") or f"RULE_{i+1:03d}")
                rule_name = str(r.get("name") or f"Corporate Policy Rule {i+1}")
                c_type = normalize_clause_type(r.get("target_clause_type"))
                sev = normalize_severity(r.get("severity"))
                triggers = [str(x) for x in (r.get("pattern_triggers") or []) if x is not None]
                forbidden = [str(x) for x in (r.get("forbidden_terms") or []) if x is not None]
                required = [str(x) for x in (r.get("required_terms") or []) if x is not None]
                fallback = str(r.get("preferred_fallback_text") or "Standard mutual terms apply.")
                comment = str(r.get("comment_explanation") or "Playbook compliance modification.")
                guidance = r.get("guidance_note")

                self.rules.append(PlaybookRule(
                    id=rule_id,
                    name=rule_name,
                    target_clause_type=c_type,
                    severity=sev,
                    pattern_triggers=triggers,
                    forbidden_terms=forbidden,
                    required_terms=required,
                    preferred_fallback_text=fallback,
                    comment_explanation=comment,
                    guidance_note=guidance,
                ))
            except Exception as e:
                print(f"[PolicyComparator] Error parsing rule at index {i}: {e}")

    def reload(self, new_path: Optional[Path] = None) -> None:
        if new_path:
            self.playbook_path = new_path
        self.load_playbook()

    def get_rules_for_type(self, clause_type: ClauseType) -> List[PlaybookRule]:
        return [r for r in self.rules if r.target_clause_type == clause_type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.playbook_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "total_rules": len(self.rules),
            "rules": [r.model_dump(mode="json") for r in self.rules]
        }

    def save_playbook(self, data: Dict[str, Any]) -> None:
        with open(self.playbook_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)
        self.load_playbook()

    def add_or_update_rule(self, rule: PlaybookRule) -> None:
        existing_idx = None
        for i, r in enumerate(self.rules):
            if r.id == rule.id:
                existing_idx = i
                break

        if existing_idx is not None:
            self.rules[existing_idx] = rule
        else:
            self.rules.append(rule)

        data = {
            "name": self.playbook_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "rules": [r.model_dump(mode="json") for r in self.rules]
        }
        self.save_playbook(data)

    def reset_to_default(self) -> None:
        if BACKUP_PLAYBOOK_PATH.exists():
            with open(BACKUP_PLAYBOOK_PATH, "r", encoding="utf-8") as src, open(self.playbook_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            self.load_playbook()
