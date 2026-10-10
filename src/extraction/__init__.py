"""
Information Extraction Package for NoticeLens (Phase 5)

Exposes:
- extract_structured_information(text, category, language)
- NoticeStructuredSchema
- ExtractionResult
"""

from src.extraction.schemas import NoticeStructuredSchema, ExtractionResult
from src.extraction.extractor import extract_structured_information

__all__ = [
    "NoticeStructuredSchema",
    "ExtractionResult",
    "extract_structured_information",
]
