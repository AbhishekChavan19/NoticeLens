"""
PDF Processing Module
Handles PDF text extraction using PyMuPDF and OCR fallback using Tesseract.
"""

from src.pdf.extractor import extract_from_pdf, ExtractionResult, PageResult

__all__ = ["extract_from_pdf", "ExtractionResult", "PageResult"]
