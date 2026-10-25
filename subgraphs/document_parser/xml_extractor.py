from pathlib import Path
from typing import List, Tuple
import docx


class DocxXMLExtractor:
    """Extracts structural paragraphs and headings from native .docx XML."""

    @staticmethod
    def extract_paragraphs(file_path: Path) -> List[Tuple[int, str, bool, str]]:
        """
        Returns list of tuples: (paragraph_index, text, is_heading, style_name)
        """
        doc = docx.Document(str(file_path))
        results = []

        for idx, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            is_bold = any(run.bold for run in p.runs if run.bold is not None)
            style_name = p.style.name if p.style else "Normal"
            is_heading_style = style_name.startswith("Heading")

            results.append((idx, text, is_heading_style or is_bold, style_name))

        return results
