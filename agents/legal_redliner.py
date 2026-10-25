from pathlib import Path
from typing import List, Optional
from core.models import Clause, RedlineAction, RedlineResult
from subgraphs.playbook_matcher import PlaybookMatcherSubgraph


class LegalRedlinerAgent:
    """
    Legal Redliner Core Agent (Section 5.2.b in PDF Synopsis).
    Checks contract terms against corporate legal playbooks.
    Identifies required changes and specifies exact clause edits.
    """

    def __init__(self, playbook_path: Optional[Path] = None):
        self.subgraph = PlaybookMatcherSubgraph(playbook_path)

    def reload_playbook(self, new_path: Optional[Path] = None) -> None:
        self.subgraph.reload_playbook(new_path)

    def review_clauses(self, clauses: List[Clause]) -> List[RedlineAction]:
        return self.subgraph.match_clauses(clauses)

    def generate_redlined_docx(
        self,
        source_docx_path: Path,
        output_docx_path: Path,
        clauses: List[Clause],
        contract_name: Optional[str] = None
    ) -> RedlineResult:
        return self.subgraph.execute(
            source_docx_path=source_docx_path,
            output_docx_path=output_docx_path,
            clauses=clauses,
            contract_name=contract_name,
        )
