from pathlib import Path
from typing import List, Optional
import yaml
from core.models import PlaybookRule, ClauseType, SeverityLevel

DEFAULT_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent.parent / "playbooks" / "enterprise_playbook.yaml"


class PolicyComparator:
    """Loads active corporate policies and compares structured clauses against playbook rules."""

    def __init__(self, playbook_path: Optional[Path] = None):
        self.playbook_path = playbook_path or DEFAULT_PLAYBOOK_PATH
        self.rules: List[PlaybookRule] = []
        self.playbook_name: str = "Enterprise Playbook"
        self.load_playbook()

    def load_playbook(self) -> None:
        if not self.playbook_path.exists():
            raise FileNotFoundError(f"Playbook file not found at {self.playbook_path}")

        with open(self.playbook_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.playbook_name = data.get("name", "Enterprise Playbook")
        raw_rules = data.get("rules", [])

        self.rules = []
        for r in raw_rules:
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

    def get_rules_for_type(self, clause_type: ClauseType) -> List[PlaybookRule]:
        return [r for r in self.rules if r.target_clause_type == clause_type]
