"""
PDF Text Extraction Module for NoticeLens

Extracts text from PDF files using PyMuPDF (fitz) with Tesseract OCR fallback.
Supports English and Marathi text extraction while preserving dates, numbers,
URLs, emails, fees, headings, and Marathi Unicode characters.

Usage:
    from src.pdf.extractor import extract_from_pdf

    with open("notice.pdf", "rb") as f:
        result = extract_from_pdf(f.read())

    print(result.extracted_text)
    print(result.extraction_method)
"""

import io
import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

import pymupdf as fitz  # PyMuPDF (using new import name)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PageResult:
    """Extraction result for a single PDF page."""

    page_number: int
    text: str
    method: str  # "text", "ocr", or "empty"
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text.strip())


@dataclass
class ExtractionResult:
    """Complete extraction result for a PDF document."""

    extracted_text: str
    page_count: int
    extraction_method: str  # "text", "ocr", "mixed", or "failed"
    per_page: list  # List[PageResult]
    warnings: list = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum non-whitespace characters to consider a page's text usable.
# Pages below this threshold trigger OCR fallback (if enabled).
MIN_USABLE_CHARS = 30

# DPI for rendering PDF pages to images for OCR.
# 300 DPI is the standard for good OCR accuracy.
OCR_DPI = 300


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_from_pdf(
    file_bytes: bytes,
    ocr_enabled: bool = True,
    tesseract_path: Optional[str] = None,
    ocr_languages: str = "eng+mar",
) -> ExtractionResult:
    """
    Extract text from a PDF file.

    This is the main entry point for the PDF extraction module.
    It first attempts normal text extraction using PyMuPDF. If a page
    yields insufficient text, it falls back to Tesseract OCR (when enabled).

    Args:
        file_bytes:      Raw bytes of the PDF file.
        ocr_enabled:     If True, use Tesseract OCR when text extraction
                         produces insufficient content. Defaults to True.
        tesseract_path:  Absolute path to the Tesseract executable.
                         Set this if Tesseract is not on the system PATH.
        ocr_languages:   Tesseract language codes separated by '+'.
                         Defaults to "eng+mar" (English + Marathi).

    Returns:
        ExtractionResult containing extracted text, metadata, and any warnings.
    """

    # --- Configure Tesseract path (if supplied) ---
    if tesseract_path and ocr_enabled:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract path set to: {tesseract_path}")
        except ImportError:
            logger.warning("pytesseract not installed; OCR will be unavailable.")
            ocr_enabled = False

    # --- Open PDF ---
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        return ExtractionResult(
            extracted_text="",
            page_count=0,
            extraction_method="failed",
            per_page=[],
            warnings=[f"Could not open PDF: {e}"],
            success=False,
            error=str(e),
        )

    # --- Password-protected check ---
    if doc.is_encrypted:
        doc.close()
        logger.warning("PDF is password-protected.")
        return ExtractionResult(
            extracted_text="",
            page_count=0,
            extraction_method="failed",
            per_page=[],
            warnings=["PDF is password-protected and cannot be read."],
            success=False,
            error="Password-protected PDF",
        )

    # --- Empty PDF check ---
    page_count = len(doc)
    if page_count == 0:
        doc.close()
        logger.warning("PDF contains no pages.")
        return ExtractionResult(
            extracted_text="",
            page_count=0,
            extraction_method="failed",
            per_page=[],
            warnings=["PDF has no pages."],
            success=False,
            error="Empty PDF (no pages)",
        )

    # --- Extract text page by page ---
    page_results: list[PageResult] = []
    warnings: list[str] = []
    methods_used: set[str] = set()

    for page_num in range(page_count):
        page = doc[page_num]
        display_num = page_num + 1  # 1-indexed for user display

        # Step 1 — Normal text extraction via PyMuPDF
        raw_text = page.get_text("text")
        cleaned_text = clean_text(raw_text)

        if is_text_usable(cleaned_text):
            # Text extraction produced enough content
            page_result = PageResult(
                page_number=display_num,
                text=cleaned_text,
                method="text",
            )
            methods_used.add("text")
            logger.info(
                f"Page {display_num}: Text extraction OK "
                f"({page_result.char_count} chars)"
            )

        elif ocr_enabled:
            # Step 2 — OCR fallback
            logger.info(
                f"Page {display_num}: Insufficient text "
                f"({len(cleaned_text.strip())} chars), attempting OCR..."
            )
            ocr_text = _ocr_page(page, ocr_languages)

            if is_text_usable(ocr_text):
                page_result = PageResult(
                    page_number=display_num,
                    text=ocr_text,
                    method="ocr",
                )
                methods_used.add("ocr")
                warnings.append(f"Page {display_num}: Used OCR fallback.")
                logger.info(
                    f"Page {display_num}: OCR succeeded "
                    f"({page_result.char_count} chars)"
                )
            else:
                # Both methods produced little text — keep the better one
                best_text = (
                    ocr_text if len(ocr_text.strip()) > len(cleaned_text.strip())
                    else cleaned_text
                )
                page_result = PageResult(
                    page_number=display_num,
                    text=best_text,
                    method="empty",
                )
                warnings.append(
                    f"Page {display_num}: Could not extract usable text "
                    f"(text: {len(cleaned_text.strip())} chars, "
                    f"OCR: {len(ocr_text.strip())} chars)."
                )
                logger.warning(f"Page {display_num}: Both methods produced little text.")

        else:
            # OCR disabled — use whatever text extraction gave us
            has_any_text = bool(cleaned_text.strip())
            page_result = PageResult(
                page_number=display_num,
                text=cleaned_text,
                method="text" if has_any_text else "empty",
            )
            if not is_text_usable(cleaned_text):
                warnings.append(
                    f"Page {display_num}: Insufficient text extracted "
                    f"({len(cleaned_text.strip())} chars) and OCR is disabled."
                )
            if has_any_text:
                methods_used.add("text")

        page_results.append(page_result)

    doc.close()

    # --- Determine overall extraction method ---
    if methods_used == {"text"}:
        overall_method = "text"
    elif methods_used == {"ocr"}:
        overall_method = "ocr"
    elif "text" in methods_used and "ocr" in methods_used:
        overall_method = "mixed"
    else:
        overall_method = "failed"

    # --- Combine page texts ---
    full_text = "\n\n".join(
        pr.text for pr in page_results if pr.text.strip()
    )

    if not full_text.strip():
        warnings.append("No usable text could be extracted from the entire PDF.")
        return ExtractionResult(
            extracted_text="",
            page_count=page_count,
            extraction_method="failed",
            per_page=page_results,
            warnings=warnings,
            success=False,
            error="No usable text extracted",
        )

    logger.info(
        f"Extraction complete: {page_count} pages, "
        f"method={overall_method}, {len(full_text)} total chars"
    )

    return ExtractionResult(
        extracted_text=full_text,
        page_count=page_count,
        extraction_method=overall_method,
        per_page=page_results,
        warnings=warnings,
        success=True,
    )


# ---------------------------------------------------------------------------
# Text Cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Clean PDF extraction artifacts while preserving important content.

    Preserves:
        - Dates, numbers, currency symbols (₹, $, etc.)
        - URLs and email addresses
        - Marathi / Devanagari Unicode characters
        - Paragraph structure and headings

    Removes:
        - Control characters (except newline, tab, carriage return)
        - Excessive whitespace within lines
        - Trailing whitespace per line
        - More than two consecutive blank lines
    """
    if not text:
        return ""

    # 1. Remove control characters (keep \n, \t, \r)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 2. Normalize non-newline whitespace sequences to a single space
    #    This collapses tabs and multiple spaces but keeps line breaks
    text = re.sub(r'[^\S\n]+', ' ', text)

    # 3. Remove trailing whitespace on each line
    text = re.sub(r' +$', '', text, flags=re.MULTILINE)

    # 4. Remove leading whitespace on each line (common PDF artifact)
    text = re.sub(r'^ +', '', text, flags=re.MULTILINE)

    # 5. Collapse 3+ consecutive blank lines into 2
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 6. Strip leading/trailing whitespace from the entire document
    text = text.strip()

    return text


# ---------------------------------------------------------------------------
# Usability Check
# ---------------------------------------------------------------------------

def is_text_usable(text: str, min_chars: int = MIN_USABLE_CHARS) -> bool:
    """
    Determine whether extracted text has enough meaningful content.

    A page with fewer than ``min_chars`` non-whitespace characters is
    considered to have insufficient text — likely a scanned image or
    a mostly-blank page.

    Args:
        text:      The extracted text to evaluate.
        min_chars: Minimum non-whitespace characters required.

    Returns:
        True if the text meets the minimum threshold.
    """
    if not text:
        return False

    meaningful = re.sub(r'\s+', '', text)
    return len(meaningful) >= min_chars


# ---------------------------------------------------------------------------
# OCR Fallback
# ---------------------------------------------------------------------------

def _ocr_page(page, languages: str = "eng+mar") -> str:
    """
    Perform OCR on a single PDF page using Tesseract.

    Renders the page to a high-resolution PNG image, then passes it
    to Tesseract for text recognition.

    Args:
        page:      A PyMuPDF page object.
        languages: Tesseract language codes (e.g. "eng+mar").

    Returns:
        Cleaned OCR text, or empty string on failure.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        logger.error(f"OCR dependency missing: {e}")
        return ""

    try:
        # Render page to image at high DPI for accurate OCR
        pix = page.get_pixmap(dpi=OCR_DPI)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        # Run Tesseract OCR with specified languages
        ocr_text = pytesseract.image_to_string(image, lang=languages)

        return clean_text(ocr_text)

    except Exception as e:
        logger.error(f"OCR failed for page: {e}")
        return ""
