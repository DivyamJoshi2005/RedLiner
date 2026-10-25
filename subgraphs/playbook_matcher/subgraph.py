from pathlib import Path
from typing import List, Optional
from core.models import Clause, RedlineAction, RedlineResult
from .policy_comparator import PolicyComparator
from .parallel_policy_checks import (
    LiabilityCompensationChecker,
    IntellectualPropertyChecker,
    LawAndGovernanceChecker,
)
from .redline_action_generator import RedlineActionGenerator
from .word_modifier import WordModifier


class PlaybookMatcherSubgraph:
    """
    Playbook Rule Matcher Subgraph (Section 5.3.b in PDF Synopsis).
    Compares structured clauses with active corporate policies.
    Runs Parallel Policy Checks across:
      1) Compensation & Liability
      2) Intellectual Property
      3) Law & Governance
    Redline Action Generator combines findings into exact edits.
    Word Modifier edits the native .docx OpenXML.
    """

    def __init__(self, playbook_path: Optional[Path] = None):
        self.comparator = PolicyComparator(playbook_path)
        self.liability_checker = LiabilityCompensationChecker()
        self.ip_checker = IntellectualPropertyChecker()
        self.law_checker = LawAndGovernanceChecker()
        self.action_generator = RedlineActionGenerator()
        self.word_modifier = WordModifier()

    def match_clauses(self, clauses: List[Clause]) -> List[RedlineAction]:
        actions: List[RedlineAction] = []
        all_rules = self.comparator.rules

        for clause in clauses:
            # Parallel check 1: Compensation & Liability
            res_liab = self.liability_checker.check(clause, all_rules)
            if res_liab.is_violation:
                act = self.action_generator.generate_action(clause, res_liab)
                if act:
                    actions.append(act)
                    continue

            # Parallel check 2: Intellectual Property
            res_ip = self.ip_checker.check(clause, all_rules)
            if res_ip.is_violation:
                act = self.action_generator.generate_action(clause, res_ip)
                if act:
                    actions.append(act)
                    continue

            # Parallel check 3: Law & Governance
            res_law = self.law_checker.check(clause, all_rules)
            if res_law.is_violation:
                act = self.action_generator.generate_action(clause, res_law)
                if act:
                    actions.append(act)
                    continue

        return actions

    def execute(
        self,
        source_docx_path: Path,
        output_docx_path: Path,
        clauses: List[Clause],
        contract_name: Optional[str] = None
    ) -> RedlineResult:
        actions = self.match_clauses(clauses)
        result = self.word_modifier.modify_docx(
            source_docx_path=source_docx_path,
            output_docx_path=output_docx_path,
            actions=actions,
            contract_name=contract_name,
        )
        return result
