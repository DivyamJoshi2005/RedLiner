import re
from typing import List, Dict, Tuple, Any
from core.models import Clause, ClauseType

CLAUSE_PATTERNS: Dict[ClauseType, Dict[str, Any]] = {
    ClauseType.LIABILITY_CAP: {
        "heading_patterns": [r"liability", r"limitation of liability", r"aggregate liability", r"damages cap"],
        "body_keywords": ["aggregate liability", "consequential damages", "indirect damages", "limitation of liability", "punitive damages", "exceed the fees", "maximum liability", "uncapped", "without limitation"],
        "weight": 1.2
    },
    ClauseType.INDEMNIFICATION: {
        "heading_patterns": [r"indemnif", r"defense", r"hold harmless"],
        "body_keywords": ["indemnify", "defend and hold harmless", "third-party claim", "infringement claim", "indemnification", "indemnitee"],
        "weight": 1.1
    },
    ClauseType.IP_RIGHTS: {
        "heading_patterns": [r"intellectual property", r"ip rights", r"proprietary rights", r"ownership", r"work product"],
        "body_keywords": ["intellectual property", "work product", "deliverables", "patents", "copyrights", "trade secrets", "background ip", "pre-existing ip", "work made for hire", "derivative works"],
        "weight": 1.1
    },
    ClauseType.GOVERNING_LAW: {
        "heading_patterns": [r"governing law", r"jurisdiction", r"dispute resolution", r"arbitration", r"applicable law"],
        "body_keywords": ["governed by", "construed in accordance with", "exclusive jurisdiction", "venue", "arbitration", "state of", "american arbitration association", "jams"],
        "weight": 1.1
    },
    ClauseType.PAYMENT_TERMS: {
        "heading_patterns": [r"payment", r"fees", r"invoicing", r"billing", r"taxes"],
        "body_keywords": ["net 30", "net 60", "net 15", "invoice", "payment terms", "late fee", "due upon receipt", "wire transfer", "taxes", "billing schedule"],
        "weight": 1.1
    },
    ClauseType.TERMINATION: {
        "heading_patterns": [r"term and termination", r"termination", r"expiration", r"cancellation"],
        "body_keywords": ["terminate for convenience", "termination for cause", "material breach", "written notice of termination", "cure period", "non-cancelable", "early termination fee", "upon 30 days"],
        "weight": 1.1
    },
    ClauseType.CONFIDENTIALITY: {
        "heading_patterns": [r"confidentiality", r"nondisclosure", r"proprietary information"],
        "body_keywords": ["confidential information", "non-disclosure", "receiving party", "disclosing party", "standard of care", "trade secrets", "injunctive relief"],
        "weight": 1.0
    },
    ClauseType.DATA_PRIVACY_SECURITY: {
        "heading_patterns": [r"data protection", r"security", r"privacy", r"data security"],
        "body_keywords": ["personal data", "security incident", "soc 2", "iso 27001", "gdpr", "ccpa", "security breach", "data protection agreement", "encryption", "subprocessors"],
        "weight": 1.1
    },
    ClauseType.WARRANTIES_REPRESENTATIONS: {
        "heading_patterns": [r"warrant", r"representations", r"disclaimer"],
        "body_keywords": ["warrants and represents", "as is", "merchantability", "fitness for a particular purpose", "express or implied warranties", "uptime", "service level"],
        "weight": 1.0
    },
    ClauseType.NON_SOLICITATION: {
        "heading_patterns": [r"non-solicitation", r"solicitation", r"non-compete"],
        "body_keywords": ["solicit any employee", "non-solicitation", "hire or solicit", "induce any employee", "twelve (12) months following"],
        "weight": 1.0
    },
    ClauseType.FORCE_MAJEURE: {
        "heading_patterns": [r"force majeure", r"acts of god"],
        "body_keywords": ["force majeure", "act of god", "natural disaster", "war, terrorism", "beyond reasonable control"],
        "weight": 1.0
    },
}


class ClauseSegmenter:
    """Segments structured paragraphs into typed contract clause objects."""

    @staticmethod
    def classify(heading: str, text: str) -> Tuple[ClauseType, float]:
        combined_content = f"{heading}\n{text}".lower()
        heading_lower = heading.lower()

        best_type = ClauseType.MISCELLANEOUS
        best_score = 0.0

        for c_type, rules in CLAUSE_PATTERNS.items():
            score = 0.0
            for hp in rules["heading_patterns"]:
                if re.search(hp, heading_lower):
                    score += 3.5

            for kw in rules["body_keywords"]:
                if kw in combined_content:
                    score += 1.0

            score *= rules.get("weight", 1.0)
            if score > best_score:
                best_score = score
                best_type = c_type

        if best_score < 1.5:
            return ClauseType.MISCELLANEOUS, 0.45

        confidence = min(0.98, max(0.65, 0.5 + (best_score / 10.0)))
        return best_type, round(confidence, 2)

    @classmethod
    def segment(cls, raw_paragraphs: List[Tuple[int, str, bool, str]]) -> List[Clause]:
        clauses: List[Clause] = []
        current_heading = "Contract Header"
        current_clause_paragraphs: List[str] = []
        current_p_index = 0

        for idx, text, is_head, _ in raw_paragraphs:
            if is_head and len(text) < 120:
                if current_clause_paragraphs:
                    clause_text = "\n".join(current_clause_paragraphs)
                    c_type, conf = cls.classify(current_heading, clause_text)
                    clauses.append(Clause(
                        id=f"clause_{len(clauses) + 1}",
                        clause_type=c_type,
                        heading=current_heading,
                        text=clause_text,
                        paragraph_index=current_p_index,
                        confidence=conf,
                        original_text=clause_text,
                    ))
                    current_clause_paragraphs = []
                current_heading = text
                current_p_index = idx
            else:
                current_clause_paragraphs.append(text)

        if current_clause_paragraphs:
            clause_text = "\n".join(current_clause_paragraphs)
            c_type, conf = cls.classify(current_heading, clause_text)
            clauses.append(Clause(
                id=f"clause_{len(clauses) + 1}",
                clause_type=c_type,
                heading=current_heading,
                text=clause_text,
                paragraph_index=current_p_index,
                confidence=conf,
                original_text=clause_text,
            ))

        return clauses
