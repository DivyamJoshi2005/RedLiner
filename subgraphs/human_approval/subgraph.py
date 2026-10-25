from .summary_agent import SummaryAgent
from .interruption_gate import InterruptionGate, FeedbackAgent


class HumanApprovalSubgraph:
    """Human Approval Subgraph (Section 5.3.e in PDF Synopsis)."""

    def __init__(self):
        self.summary_agent = SummaryAgent()
        self.interruption_gate = InterruptionGate()
        self.feedback_agent = FeedbackAgent()
