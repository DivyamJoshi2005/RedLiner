class InterruptionGate:
    """Pauses deals that go beyond thresholds and awaits human review (PDF 5.3.e)."""

    @staticmethod
    def should_interrupt(critical_violations: int, vendor_risk_score: float) -> bool:
        # Pauses execution when critical terms are violated or vendor risk >= 50
        return critical_violations > 0 or vendor_risk_score >= 50.0


class FeedbackAgent:
    """Receives approve, reject, or manual edit decisions from the dashboard (PDF 5.3.e)."""

    VALID_DECISIONS = ["APPROVE", "REJECT", "MANUAL_EDIT"]

    @staticmethod
    def process_decision(decision: str, reviewer_notes: str = "") -> dict:
        dec_upper = decision.upper()
        if dec_upper not in FeedbackAgent.VALID_DECISIONS:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of {FeedbackAgent.VALID_DECISIONS}")

        return {
            "decision": dec_upper,
            "can_dispatch": dec_upper == "APPROVE",
            "needs_renegotiation": dec_upper in ["REJECT", "MANUAL_EDIT"],
            "notes": reviewer_notes
        }
