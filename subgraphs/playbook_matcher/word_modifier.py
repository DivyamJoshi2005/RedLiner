import html
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
import docx
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from core.models import RedlineAction, RedlineResult
from Helpers.logger import log_redline_audit

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"


def _escape_xml(text: str) -> str:
    return html.escape(text, quote=True)


class WordModifier:
    """
    Edits native Word .docx XML to insert tracked deletions (<w:del>),
    tracked insertions (<w:ins>), and margin comments (<w:comment> in word/comments.xml).
    """

    def __init__(self, author: str = "RedLiner Legal AI", initials: str = "RL"):
        self.author = author
        self.initials = initials

    def modify_docx(
        self,
        source_docx_path: Path,
        output_docx_path: Path,
        actions: List[RedlineAction],
        contract_name: Optional[str] = None,
    ) -> RedlineResult:
        doc = docx.Document(str(source_docx_path))
        contract_title = contract_name or source_docx_path.stem
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        comment_entries: List[Dict[str, str]] = []
        next_revision_id = 100
        next_comment_id = 0

        action_map: Dict[int, List[RedlineAction]] = {}
        for action in actions:
            p_idx = action.target_paragraph_index
            if p_idx not in action_map:
                action_map[p_idx] = []
            action_map[p_idx].append(action)

        paragraphs = doc.paragraphs

        for p_idx, p_actions in action_map.items():
            if p_idx >= len(paragraphs):
                continue

            target_p = paragraphs[p_idx]
            original_text = target_p.text

            if not original_text.strip() and p_idx + 1 < len(paragraphs):
                target_p = paragraphs[p_idx + 1]
                original_text = target_p.text

            for act in p_actions:
                c_id = next_comment_id
                next_comment_id += 1
                del_rev_id = next_revision_id
                ins_rev_id = next_revision_id + 1
                next_revision_id += 2

                comment_entries.append({
                    "id": str(c_id),
                    "author": self.author,
                    "initials": self.initials,
                    "date": timestamp,
                    "text": act.comment,
                })

                for r in list(target_p.runs):
                    target_p._p.remove(r._r)

                del_text_escaped = _escape_xml(act.original_text if act.original_text else original_text)
                ins_text_escaped = _escape_xml(act.replacement_text)

                # 1. Comment range start
                range_start = parse_xml(f'<w:commentRangeStart {nsdecls("w")} w:id="{c_id}"/>')
                target_p._p.append(range_start)

                # 2. Tracked Deletion (<w:del>)
                del_xml = parse_xml(
                    f'<w:del {nsdecls("w")} w:id="{del_rev_id}" w:author="{_escape_xml(self.author)}" w:date="{timestamp}">'
                    f'  <w:r>'
                    f'    <w:rPr><w:strike/></w:rPr>'
                    f'    <w:delText xml:space="preserve">{del_text_escaped}</w:delText>'
                    f'  </w:r>'
                    f'</w:del>'
                )
                target_p._p.append(del_xml)

                # 3. Tracked Insertion (<w:ins>)
                ins_xml = parse_xml(
                    f'<w:ins {nsdecls("w")} w:id="{ins_rev_id}" w:author="{_escape_xml(self.author)}" w:date="{timestamp}">'
                    f'  <w:r>'
                    f'    <w:rPr><w:u w:val="single"/></w:rPr>'
                    f'    <w:t xml:space="preserve"> {ins_text_escaped}</w:t>'
                    f'  </w:r>'
                    f'</w:ins>'
                )
                target_p._p.append(ins_xml)

                # 4. Comment range end
                range_end = parse_xml(f'<w:commentRangeEnd {nsdecls("w")} w:id="{c_id}"/>')
                target_p._p.append(range_end)

                # 5. Comment reference
                ref_run = parse_xml(
                    f'<w:r {nsdecls("w")}>'
                    f'  <w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
                    f'  <w:commentReference w:id="{c_id}"/>'
                    f'</w:r>'
                )
                target_p._p.append(ref_run)

        if comment_entries:
            self._inject_comments_part(doc, comment_entries)

        output_docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_docx_path))

        critical_count = sum(1 for a in actions if a.severity.value == "CRITICAL")
        summary_text = (
            f"Successfully applied {len(actions)} redlines ({critical_count} critical) "
            f"to '{contract_title}'. Native tracked changes and margin comments generated."
        )

        log_redline_audit(
            contract_name=contract_title,
            playbook_used="Enterprise Legal Playbook",
            total_clauses=len(paragraphs),
            violations_detected=len(actions),
            critical_violations=critical_count,
            actions_generated=len(actions),
            output_docx_path=str(output_docx_path),
            actions_summary=[
                {
                    "rule": a.rule_name,
                    "clause_type": a.clause_type.value,
                    "severity": a.severity.value,
                    "action": a.action_type.value,
                }
                for a in actions
            ],
        )

        return RedlineResult(
            contract_name=contract_title,
            total_clauses=len(paragraphs),
            violations_detected=len(actions),
            critical_count=critical_count,
            actions=actions,
            output_docx_filename=output_docx_path.name,
            output_docx_path=str(output_docx_path),
            summary=summary_text,
        )

    def _inject_comments_part(self, doc: docx.Document, comments: List[Dict[str, str]]) -> None:
        comments_xml_parts: List[str] = [f'<w:comments {nsdecls("w")}>']

        for c in comments:
            comment_text_escaped = _escape_xml(c["text"])
            comments_xml_parts.append(
                f'  <w:comment w:id="{c["id"]}" w:author="{_escape_xml(c["author"])}" '
                f'w:date="{c["date"]}" w:initials="{_escape_xml(c["initials"])}">'
                f'    <w:p>'
                f'      <w:pPr><w:pStyle w:val="CommentText"/></w:pPr>'
                f'      <w:r><w:t xml:space="preserve">{comment_text_escaped}</w:t></w:r>'
                f'    </w:p>'
                f'  </w:comment>'
            )

        comments_xml_parts.append('</w:comments>')
        xml_content = "\n".join(comments_xml_parts).encode("utf-8")

        existing_part = None
        for rel in doc.part.rels.values():
            if rel.reltype == COMMENTS_REL_TYPE:
                existing_part = rel.target_ref
                break

        if not existing_part:
            comments_part = Part(
                PackURI("/word/comments.xml"),
                COMMENTS_CONTENT_TYPE,
                xml_content,
                doc.part.package,
            )
            doc.part.relate_to(comments_part, COMMENTS_REL_TYPE)
