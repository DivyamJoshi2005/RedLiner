import time
from pathlib import Path
from typing import Dict
from core.models import ParsedDocument
from Helpers.logger import log_parser_metadata
from .xml_extractor import DocxXMLExtractor
from .pdf_extractor import PDFExtractor
from .clause_segmenter import ClauseSegmenter


class DocumentParserSubgraph:
    """
    Document Parser Subgraph (Section 5.3.a in PDF Synopsis).
    Receives vendor .docx and .pdf attachments, extracts XML/text,
    and runs ClauseSegmenter to produce an indexed array of typed clause objects.
    """

    def __init__(self):
        self.xml_extractor = DocxXMLExtractor()
        self.pdf_extractor = PDFExtractor()
        self.segmenter = ClauseSegmenter()

    def execute(self, file_path: Path) -> ParsedDocument:
        start_time = time.time()
        ext = file_path.suffix.lower()

        if ext == ".docx":
            raw_paras = self.xml_extractor.extract_paragraphs(file_path)
            file_type = "docx"
        elif ext == ".pdf":
            raw_paras = self.pdf_extractor.extract_paragraphs(file_path)
            file_type = "pdf"
        else:
            raise ValueError(f"Unsupported contract format '{ext}' in DocumentParserSubgraph.")

        clauses = self.segmenter.segment(raw_paras)
        elapsed_ms = (time.time() - start_time) * 1000.0

        distribution: Dict[str, int] = {}
        for c in clauses:
            distribution[c.clause_type.value] = distribution.get(c.clause_type.value, 0) + 1

        parsed_doc = ParsedDocument(
            filename=file_path.name,
            file_type=file_type,
            total_paragraphs=len(raw_paras),
            clauses=clauses,
            clause_distribution=distribution,
            raw_text="\n\n".join(p[1] for p in raw_paras),
        )

        log_parser_metadata(
            filename=file_path.name,
            file_type=file_type,
            paragraphs_count=len(raw_paras),
            clauses_identified=len(clauses),
            clause_types_found=list(distribution.keys()),
            elapsed_ms=elapsed_ms,
            extra={"distribution": distribution},
        )

        return parsed_doc
