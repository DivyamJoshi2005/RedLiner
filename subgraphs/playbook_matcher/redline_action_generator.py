from typing import List, Optional
from core.models import Clause, RedlineAction, ActionType
from .parallel_policy_checks import PolicyCheckResult


class RedlineActionGenerator:
    """Combines policy findings into exact strikethroughs, replacements, and margin comments."""

    @staticmethod
    def generate_action(clause: Clause, check_result: PolicyCheckResult) -> Optional[RedlineAction]:
        if not check_result.is_violation or not check_result.rule:
            return None

        rule = check_result.rule
        reasons_str = "; ".join(check_result.reasons)

        comment_body = (
            f"{rule.comment_explanation}\n\n"
            f"[Policy Violation]: {reasons_str}\n"
            f"[Risk Severity]: {rule.severity.value}\n"
            f"[Playbook Rule]: {rule.name} ({rule.id})"
        )

        return RedlineAction(
            action_id=f"act_{rule.id.lower()}_{clause.id}",
            clause_id=clause.id,
            clause_type=clause.clause_type,
            action_type=ActionType.REPLACE,
            target_paragraph_index=clause.paragraph_index,
            original_text=clause.text,
            replacement_text=rule.preferred_fallback_text,
            comment=comment_body,
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
        )
