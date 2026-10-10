"""
Unit Tests for Information Extraction Module (Phase 5)

Run with:
    python -m pytest tests/test_extraction.py -v
"""

import os
import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.extraction.schemas import NoticeStructuredSchema, ExtractionResult
from src.extraction.extractor import extract_structured_information


# ---------------------------------------------------------------------------
# Sample Stored Notices
# ---------------------------------------------------------------------------

SAMPLE_EXAM_NOTICE = """
PIMPRI CHINCHWAD COLLEGE OF ENGINEERING
NOTICE - EXAMINATION DEPARTMENT
Ref. No. PCCoE/EXAM/2024/102. Date: 15/10/2024

All final year B.Tech students are hereby informed that the End Semester Examination (ESE)
fees of Rs. 1500 must be paid online before 30/10/2024 through the student portal
www.pccoepune.org.

Documents required for verification:
1. Marksheets of previous semesters
2. Identity Card

For any queries contact exam section: exam@pccoepune.org / 020-27653168.
"""

SAMPLE_MARATHI_NOTICE = """
पिंपरी चिंचवड अभियांत्रिकी महाविद्यालय, निगडी, पुणे.
सूचना - प्रवेश कक्ष
दिनांक: २० ऑगस्ट २०२४.

सर्व प्रथम वर्ष बी.टेक प्रवेश घेतलेल्या विद्यार्थ्यांचे स्वागत समारंभ
दिनांक २५ ऑगस्ट २०२४ रोजी सकाळी १०.०० वाजता अनुपम सभागृहात आयोजित केला आहे.
उपस्थिती अनिवार्य आहे.
"""


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_pydantic_schema_validation():
    """Test schema parsing, default values, and type validation."""
    data = {
        "title": "NOTICE - EXAMINATION DEPARTMENT",
        "category": "Examination",
        "language": "English",
        "what_is_this_about": "End Semester Examination fee submission",
        "target_audience": "Final Year B.Tech students",
        "action_required": True,
        "actions": ["Pay exam fee online", "Submit marksheets for verification"],
        "deadline": "30/10/2024",
        "important_dates": ["15/10/2024", "30/10/2024"],
        "documents_required": ["Marksheets of previous semesters", "Identity Card"],
        "fees": "Rs. 1500",
        "eligibility": None,
        "venue": None,
        "portal_or_link": "www.pccoepune.org",
        "contact_information": "exam@pccoepune.org / 020-27653168",
    }

    schema = NoticeStructuredSchema(**data)
    assert schema.title == "NOTICE - EXAMINATION DEPARTMENT"
    assert schema.action_required is True
    assert len(schema.documents_required) == 2
    assert schema.eligibility is None
    assert schema.venue is None


def test_missing_fields_return_null_or_empty_list():
    """Verify that absent fields default to None or [] as per Accuracy Rules."""
    schema = NoticeStructuredSchema(
        category="Academics",
        language="Marathi",
    )
    assert schema.title is None
    assert schema.what_is_this_about is None
    assert schema.deadline is None
    assert schema.fees is None
    assert schema.actions == []
    assert schema.important_dates == []
    assert schema.documents_required == []


def test_missing_api_key_handling():
    """Test that missing API key returns a structured error without fabricating data."""
    with patch.dict(os.environ, {}, clear=True):
        res = extract_structured_information(
            text=SAMPLE_EXAM_NOTICE,
            category="Examination",
            language="English",
            api_key=None,
        )
        assert res.success is False
        assert res.data is None
        assert "OPENAI_API_KEY" in res.error or "GROQ_API_KEY" in res.error or "API" in res.error
        assert res.original_text == SAMPLE_EXAM_NOTICE


def test_mocked_openai_structured_extraction():
    """Test extraction function with mocked OpenAI API client."""
    mock_parsed_data = NoticeStructuredSchema(
        title="NOTICE - EXAMINATION DEPARTMENT",
        category="Examination",
        language="English",
        what_is_this_about="End semester examination fee payment",
        target_audience="Final year B.Tech students",
        action_required=True,
        actions=["Pay exam fee online"],
        deadline="30/10/2024",
        important_dates=["15/10/2024", "30/10/2024"],
        documents_required=["Marksheets of previous semesters", "Identity Card"],
        fees="Rs. 1500",
        eligibility=None,
        venue=None,
        portal_or_link="www.pccoepune.org",
        contact_information="exam@pccoepune.org / 020-27653168",
    )

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # Mock beta.chat.completions.parse response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.parsed = mock_parsed_data
        mock_client.beta.chat.completions.parse.return_value = mock_completion

        res = extract_structured_information(
            text=SAMPLE_EXAM_NOTICE,
            category="Examination",
            language="English",
            api_key="fake-key-for-test",
        )

        assert res.success is True
        assert res.data is not None
        assert res.data.category == "Examination"
        assert res.data.deadline == "30/10/2024"
        assert res.data.fees == "Rs. 1500"
        assert res.original_text == SAMPLE_EXAM_NOTICE


def test_api_failure_error_handling():
    """Test that API exception returns useful error message without fabricating data."""
    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.beta.chat.completions.parse.side_effect = Exception("Rate limit exceeded")

        res = extract_structured_information(
            text=SAMPLE_MARATHI_NOTICE,
            category="Admission",
            language="Marathi",
            api_key="fake-key-for-test",
        )

        assert res.success is False
        assert res.data is None
        assert "Rate limit exceeded" in res.error
        assert res.original_text == SAMPLE_MARATHI_NOTICE
