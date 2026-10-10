"""
Tests for the PDF Text Extraction Module

Run with:
    python -m pytest tests/test_pdf_extraction.py -v
"""

import os
import sys

import pytest

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.extractor import (
    extract_from_pdf,
    clean_text,
    is_text_usable,
    ExtractionResult,
    PageResult,
)


# -----------------------------------------------------------------------
# Tests for clean_text()
# -----------------------------------------------------------------------

class TestCleanText:
    """Tests for the text cleaning function."""

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none_input(self):
        assert clean_text(None) == ""

    def test_removes_control_characters(self):
        text = "Hello\x00World\x07Test"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x07" not in result
        assert "Hello" in result
        assert "World" in result

    def test_preserves_newlines(self):
        text = "Line 1\nLine 2\nLine 3"
        result = clean_text(text)
        assert "Line 1" in result
        assert "Line 2" in result
        assert result.count("\n") >= 2

    def test_collapses_excessive_blank_lines(self):
        text = "Para 1\n\n\n\n\n\nPara 2"
        result = clean_text(text)
        # Should collapse to at most 3 newlines (2 blank lines)
        assert "\n\n\n\n" not in result
        assert "Para 1" in result
        assert "Para 2" in result

    def test_collapses_excessive_spaces(self):
        text = "Hello     World     Test"
        result = clean_text(text)
        assert "     " not in result
        assert "Hello World Test" == result

    def test_strips_trailing_whitespace(self):
        text = "Hello   \nWorld   \n"
        result = clean_text(text)
        lines = result.split("\n")
        for line in lines:
            assert line == line.rstrip(), f"Line has trailing whitespace: '{line}'"

    def test_preserves_dates(self):
        text = "Exam date: 15/03/2025 and 2025-01-20"
        result = clean_text(text)
        assert "15/03/2025" in result
        assert "2025-01-20" in result

    def test_preserves_numbers_and_currency(self):
        text = "Fee: ₹5,000 or $100 or Rs. 2500/-"
        result = clean_text(text)
        assert "₹5,000" in result
        assert "$100" in result
        assert "Rs. 2500/-" in result

    def test_preserves_urls(self):
        text = "Visit https://www.pccoepune.com/notices for details."
        result = clean_text(text)
        assert "https://www.pccoepune.com/notices" in result

    def test_preserves_email_addresses(self):
        text = "Contact us at exam@pccoe.edu.in for queries."
        result = clean_text(text)
        assert "exam@pccoe.edu.in" in result

    def test_preserves_marathi_text(self):
        text = "सूचना: परीक्षा दिनांक 15 मार्च 2025 रोजी आहे."
        result = clean_text(text)
        assert "सूचना" in result
        assert "परीक्षा" in result
        assert "15" in result
        assert "2025" in result

    def test_preserves_bilingual_text(self):
        text = "Notice / सूचना\nExam Date: 15/03/2025\nपरीक्षा दिनांक: 15/03/2025"
        result = clean_text(text)
        assert "Notice" in result
        assert "सूचना" in result
        assert "15/03/2025" in result


# -----------------------------------------------------------------------
# Tests for is_text_usable()
# -----------------------------------------------------------------------

class TestIsTextUsable:
    """Tests for the text usability check."""

    def test_empty_string(self):
        assert is_text_usable("") is False

    def test_none_input(self):
        assert is_text_usable(None) is False

    def test_whitespace_only(self):
        assert is_text_usable("   \n\n\t  ") is False

    def test_short_text(self):
        assert is_text_usable("Hi") is False

    def test_sufficient_text(self):
        text = "This notice is regarding the upcoming examination schedule for all students."
        assert is_text_usable(text) is True

    def test_custom_threshold(self):
        text = "Short text"
        assert is_text_usable(text, min_chars=5) is True
        assert is_text_usable(text, min_chars=50) is False

    def test_marathi_text_usable(self):
        text = "सर्व विद्यार्थ्यांना सूचित करण्यात येते की परीक्षा दिनांक बदलण्यात आला आहे."
        assert is_text_usable(text) is True


# -----------------------------------------------------------------------
# Tests for extract_from_pdf()
# -----------------------------------------------------------------------

class TestExtractFromPdf:
    """Tests for the main PDF extraction function."""

    def test_invalid_bytes(self):
        """Passing garbage bytes should return a failed result."""
        result = extract_from_pdf(b"this is not a pdf")
        assert result.success is False
        assert result.extraction_method == "failed"
        assert result.error is not None
        assert len(result.warnings) > 0

    def test_empty_bytes(self):
        """Passing empty bytes should return a failed result."""
        result = extract_from_pdf(b"")
        assert result.success is False
        assert result.extraction_method == "failed"

    def test_result_structure(self):
        """ExtractionResult should have all expected fields."""
        result = ExtractionResult(
            extracted_text="test",
            page_count=1,
            extraction_method="text",
            per_page=[PageResult(page_number=1, text="test", method="text")],
            warnings=[],
            success=True,
        )
        assert result.extracted_text == "test"
        assert result.page_count == 1
        assert result.extraction_method == "text"
        assert len(result.per_page) == 1
        assert result.per_page[0].char_count == 4
        assert result.success is True
        assert result.error is None

    def test_page_result_char_count(self):
        """PageResult should auto-calculate char_count."""
        pr = PageResult(page_number=1, text="  hello world  ", method="text")
        assert pr.char_count == len("  hello world  ".strip())


# -----------------------------------------------------------------------
# Integration Test — Real PDF from data/raw/ (if available)
# -----------------------------------------------------------------------

class TestRealPdfExtraction:
    """Integration tests using actual PDFs from the data/raw/ directory."""

    DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "raw",
    )

    def _get_first_pdf(self):
        """Find the first PDF file in data/raw/."""
        if not os.path.isdir(self.DATA_DIR):
            return None
        for f in sorted(os.listdir(self.DATA_DIR)):
            if f.lower().endswith(".pdf"):
                return os.path.join(self.DATA_DIR, f)
        return None

    @pytest.mark.skipif(
        not os.path.isdir(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "raw",
            )
        ),
        reason="data/raw/ directory not found",
    )
    def test_real_pdf_extraction(self):
        """Extract text from a real PDF and verify the result structure."""
        pdf_path = self._get_first_pdf()
        if pdf_path is None:
            pytest.skip("No PDF files found in data/raw/")

        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        result = extract_from_pdf(file_bytes, ocr_enabled=False)

        # Verify structure
        assert isinstance(result, ExtractionResult)
        assert result.page_count > 0
        assert len(result.per_page) == result.page_count
        assert result.extraction_method in ("text", "ocr", "mixed", "failed")

        # If extraction succeeded, text should be non-empty
        if result.success:
            assert len(result.extracted_text) > 0
            print(f"\n--- Extracted from {os.path.basename(pdf_path)} ---")
            print(f"Pages: {result.page_count}")
            print(f"Method: {result.extraction_method}")
            print(f"Total chars: {len(result.extracted_text)}")
            print(f"First 300 chars:\n{result.extracted_text[:300]}")
