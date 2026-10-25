from pathlib import Path
from typing import List, Tuple
import pypdf
import re


class PDFExtractor:
    """Extracts digital text from PDF agreements without requiring OCR."""

    @staticmethod
    def extract_paragraphs(file_path: Path) -> List[Tuple[int, str, bool, str]]:
        reader = pypdf.PdfReader(str(file_path))
        extracted_lines: List[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            current_para = []
            for line in lines:
                is_head = PDFExtractor.is_heading_pattern(line)
                if is_head:
                    if current_para:
                        extracted_lines.append(" ".join(current_para))
                        current_para = []
                    extracted_lines.append(line)
                else:
                    current_para.append(line)
            if current_para:
                extracted_lines.append(" ".join(current_para))

        results = []
        for idx, line in enumerate(extracted_lines):
            is_head = PDFExtractor.is_heading_pattern(line)
            results.append((idx, line, is_head, "Heading" if is_head else "Normal"))

        return results

    @staticmethod
    def is_heading_pattern(text: str) -> bool:
        if not text:
            return False
        if re.match(r"^(section|article|clause)?\s*(\d+(\.\d+)*|[ivxlcdm]+)[\.\:\-\s]+[A-Za-z]", text, re.IGNORECASE):
            return len(text) < 120
        if text.isupper() and len(text) < 80:
            return True
        return False
