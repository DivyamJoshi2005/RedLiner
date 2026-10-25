import re
from typing import List, Optional, Tuple
from core.models import Clause, ClauseType, PlaybookRule


class PolicyCheckResult:
    def __init__(self, is_violation: bool, rule: Optional[PlaybookRule] = None, reasons: Optional[List[str]] = None):
        self.is_violation = is_violation
        self.rule = rule
        self.reasons = reasons or []


class LiabilityCompensationChecker:
    """Evaluates caps against deal value, consequential damages, and payment terms."""

    @staticmethod
    def check(clause: Clause, rules: List[PlaybookRule]) -> PolicyCheckResult:
        if clause.clause_type not in [ClauseType.LIABILITY_CAP, ClauseType.PAYMENT_TERMS]:
            return PolicyCheckResult(False)

        content = f"{clause.heading}\n{clause.text}".lower()
        for rule in rules:
            if rule.target_clause_type != clause.clause_type:
                continue

            for forbidden in rule.forbidden_terms:
                if forbidden.lower() in content:
                    return PolicyCheckResult(True, rule, [f"Forbidden term in liability/payment: '{forbidden}'"])

            for pattern in rule.pattern_triggers:
                if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", content):
                    return PolicyCheckResult(True, rule, [f"Liability/payment limit trigger: '{pattern}'"])

            if rule.required_terms:
                missing = [req for req in rule.required_terms if req.lower() not in content]
                if len(missing) >= len(rule.required_terms) - 1 and len(clause.text) > 80:
                    return PolicyCheckResult(True, rule, [f"Missing mandatory liability protection: {', '.join(missing)}"])

        return PolicyCheckResult(False)


class IntellectualPropertyChecker:
    """Evaluates deliverables ownership, derivative works, and customer data rights."""

    @staticmethod
    def check(clause: Clause, rules: List[PlaybookRule]) -> PolicyCheckResult:
        if clause.clause_type != ClauseType.IP_RIGHTS:
            return PolicyCheckResult(False)

        content = f"{clause.heading}\n{clause.text}".lower()
        for rule in rules:
            if rule.target_clause_type != ClauseType.IP_RIGHTS:
                continue

            for forbidden in rule.forbidden_terms:
                if forbidden.lower() in content:
                    return PolicyCheckResult(True, rule, [f"Forbidden term in IP ownership: '{forbidden}'"])

            for pattern in rule.pattern_triggers:
                if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", content):
                    return PolicyCheckResult(True, rule, [f"Unacceptable IP assignment trigger: '{pattern}'"])

            if rule.required_terms:
                missing = [req for req in rule.required_terms if req.lower() not in content]
                if len(missing) >= len(rule.required_terms) - 1 and len(clause.text) > 80:
                    return PolicyCheckResult(True, rule, [f"Missing customer IP retention terms: {', '.join(missing)}"])

        return PolicyCheckResult(False)


class LawAndGovernanceChecker:
    """Evaluates governing law, jurisdiction, indemnification, and termination."""

    @staticmethod
    def check(clause: Clause, rules: List[PlaybookRule]) -> PolicyCheckResult:
        # Evaluates governing law, indemnification, termination, privacy, confidentiality, and any custom playbook clauses
        if clause.clause_type in [ClauseType.LIABILITY_CAP, ClauseType.PAYMENT_TERMS, ClauseType.IP_RIGHTS]:
            return PolicyCheckResult(False)

        content = f"{clause.heading}\n{clause.text}".lower()
        for rule in rules:
            if rule.target_clause_type != clause.clause_type:
                continue

            for forbidden in rule.forbidden_terms:
                if forbidden.lower() in content:
                    return PolicyCheckResult(True, rule, [f"Forbidden governance term: '{forbidden}'"])

            for pattern in rule.pattern_triggers:
                if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", content):
                    return PolicyCheckResult(True, rule, [f"Governance trigger: '{pattern}'"])

            if rule.required_terms:
                missing = [req for req in rule.required_terms if req.lower() not in content]
                if len(missing) >= len(rule.required_terms) - 1 and len(clause.text) > 80:
                    return PolicyCheckResult(True, rule, [f"Missing mandatory governance term: {', '.join(missing)}"])

        return PolicyCheckResult(False)
