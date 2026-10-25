from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from core.models import PlaybookRule, ClauseType, SeverityLevel

DEFAULT_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "playbooks" / "enterprise_playbook.yaml"
BACKUP_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "playbooks" / "enterprise_playbook.backup.yaml"


class PolicyComparator:
    """Loads active corporate policies and compares structured clauses against playbook rules."""

    def __init__(self, playbook_path: Optional[Path] = None):
        self.playbook_path = playbook_path or DEFAULT_PLAYBOOK_PATH
        self.rules: List[PlaybookRule] = []
        self.playbook_name: str = "Enterprise Playbook"
        self.version: str = "2026.1"
        self.description: str = ""
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
        for r in raw_rules:
            try:
                self.rules.append(PlaybookRule(
                    id=r["id"],
                    name=r["name"],
                    target_clause_type=ClauseType(r["target_clause_type"]),
                    severity=SeverityLevel(r["severity"]),
                    pattern_triggers=r.get("pattern_triggers", []),
                    forbidden_terms=r.get("forbidden_terms", []),
                    required_terms=r.get("required_terms", []),
                    preferred_fallback_text=r["preferred_fallback_text"],
                    comment_explanation=r["comment_explanation"],
                    guidance_note=r.get("guidance_note"),
                ))
            except Exception as e:
                print(f"[PolicyComparator] Error parsing rule {r.get('id')}: {e}")

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
