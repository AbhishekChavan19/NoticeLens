"""
Unit Tests for Phase 6: Notice Simplification Module

Tests use mocked OpenAI API responses to validate:
- Correct schema output for English and Marathi
- Handling of missing/absent fields
- API key validation
- Error handling for API failures
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.extraction.schemas import NoticeStructuredSchema
from src.simplification.schemas import (
    SimplifiedEnglish,
    SimplifiedMarathi,
    SimplificationResult,
)
from src.simplification.simplifier import simplify_notice


# ── Sample structured data from Phase 5 ──────────────────────────────────

SAMPLE_STRUCTURED_DATA = NoticeStructuredSchema(
    title="End Semester Examination Timetable - B.Tech Semester VII",
    category="Examination",
    language="English",
    what_is_this_about="End semester examination timetable for B.Tech Semester VII students.",
    target_audience="B.Tech Semester VII students",
    action_required=True,
    actions=[
        "Check the timetable for your subjects.",
        "Carry your hall ticket to the examination hall.",
    ],
    deadline="15th November 2026",
    important_dates=["15th November 2026 - Exam starts", "30th November 2026 - Exam ends"],
    documents_required=["Hall Ticket", "College ID Card"],
    fees=None,
    eligibility="Students with minimum 75% attendance",
    venue="Main Examination Hall, Block A",
    portal_or_link="https://pccoe.exam-portal.edu",
    contact_information="Exam Cell - exam@pccoe.org, Ext: 1234",
)

MINIMAL_STRUCTURED_DATA = NoticeStructuredSchema(
    title=None,
    category="General",
    language="Marathi",
    what_is_this_about="General college announcement.",
    target_audience=None,
    action_required=False,
    actions=[],
    deadline=None,
    important_dates=[],
    documents_required=[],
    fees=None,
    eligibility=None,
    venue=None,
    portal_or_link=None,
    contact_information=None,
)


# ── Mock responses ──────────────────────────────────────────────────────────

MOCK_ENGLISH_RESPONSE = json.dumps({
    "what_is_this_notice_about": "This notice shares the end semester exam timetable for 7th semester B.Tech students.",
    "who_is_it_for": "B.Tech Semester VII students",
    "what_do_i_need_to_do": "Check the timetable for your subjects and carry your hall ticket.",
    "deadline": "15th November 2026",
    "important_dates": "15th November 2026 - Exam starts, 30th November 2026 - Exam ends",
    "documents_required": "Hall Ticket, College ID Card",
    "fees": None,
    "eligibility": "Students with minimum 75% attendance",
    "important_note": "Visit https://pccoe.exam-portal.edu for details. Contact Exam Cell at exam@pccoe.org",
})

MOCK_MARATHI_RESPONSE = json.dumps({
    "हा_नोटीस_कशाबद्दल_आहे": "हा नोटीस B.Tech सातव्या सत्राच्या अंतिम परीक्षा वेळापत्रकाबद्दल आहे.",
    "कोणासाठी_आहे": "B.Tech सातव्या सत्राचे विद्यार्थी",
    "मला_काय_करावे_लागेल": "तुमच्या विषयांचे वेळापत्रक तपासा आणि हॉल तिकीट सोबत ठेवा.",
    "अंतिम_तारीख": "१५ नोव्हेंबर २०२६",
    "महत्त्वाच्या_तारखा": "१५ नोव्हेंबर २०२६ - परीक्षा सुरू, ३० नोव्हेंबर २०२६ - परीक्षा संपेल",
    "आवश्यक_कागदपत्रे": "हॉल तिकीट, कॉलेज ओळखपत्र",
    "फी": None,
    "पात्रता": "किमान ७५% उपस्थिती असलेले विद्यार्थी",
    "महत्त्वाची_सूचना": "तपशीलांसाठी https://pccoe.exam-portal.edu ला भेट द्या.",
})


# ── Helper to build mock client ──────────────────────────────────────────────

def _build_mock_client(english_json: str, marathi_json: str):
    """Build a mock OpenAI client that returns structured json_object responses."""
    mock_client = MagicMock()

    # Make beta.chat.completions.parse raise AttributeError to trigger json_object fallback
    mock_client.beta.chat.completions.parse.side_effect = AttributeError("mock structured parse failure")

    # json_object fallback responses — called twice (English, then Marathi)
    mock_english_choice = MagicMock()
    mock_english_choice.message.content = english_json

    mock_marathi_choice = MagicMock()
    mock_marathi_choice.message.content = marathi_json

    mock_english_completion = MagicMock()
    mock_english_completion.choices = [mock_english_choice]

    mock_marathi_completion = MagicMock()
    mock_marathi_completion.choices = [mock_marathi_choice]

    mock_client.chat.completions.create.side_effect = [
        mock_english_completion,
        mock_marathi_completion,
    ]

    return mock_client


# ── Test cases ──────────────────────────────────────────────────────────────


class TestSimplifyNotice:
    """Test suite for the simplify_notice function."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-12345"})
    @patch("openai.OpenAI")
    def test_successful_simplification(self, mock_openai_class):
        """Full structured data should produce valid English + Marathi output."""
        mock_openai_class.return_value = _build_mock_client(
            MOCK_ENGLISH_RESPONSE, MOCK_MARATHI_RESPONSE
        )

        result = simplify_notice(
            extracted_data=SAMPLE_STRUCTURED_DATA,
            api_key="test-key-12345",
        )

        assert result.success is True
        assert result.error is None

        # English checks
        assert result.simple_english is not None
        assert "exam" in result.simple_english.what_is_this_notice_about.lower()
        assert result.simple_english.deadline == "15th November 2026"
        assert result.simple_english.fees is None

        # Marathi checks
        assert result.simple_marathi is not None
        assert "परीक्षा" in result.simple_marathi.notice_about

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-12345"})
    @patch("openai.OpenAI")
    def test_minimal_data_simplification(self, mock_openai_class):
        """Minimal data with mostly null fields should still succeed."""
        mock_english_minimal = json.dumps({
            "what_is_this_notice_about": "General college announcement.",
            "who_is_it_for": "All students",
            "what_do_i_need_to_do": "No specific action required.",
            "deadline": None,
            "important_dates": None,
            "documents_required": None,
            "fees": None,
            "eligibility": None,
            "important_note": None,
        })
        mock_marathi_minimal = json.dumps({
            "हा_नोटीस_कशाबद्दल_आहे": "सामान्य कॉलेज घोषणा.",
            "कोणासाठी_आहे": "सर्व विद्यार्थी",
            "मला_काय_करावे_लागेल": "विशिष्ट कृती आवश्यक नाही.",
            "अंतिम_तारीख": None,
            "महत्त्वाच्या_तारखा": None,
            "आवश्यक_कागदपत्रे": None,
            "फी": None,
            "पात्रता": None,
            "महत्त्वाची_सूचना": None,
        })

        mock_openai_class.return_value = _build_mock_client(
            mock_english_minimal, mock_marathi_minimal
        )

        result = simplify_notice(
            extracted_data=MINIMAL_STRUCTURED_DATA,
            api_key="test-key-12345",
        )

        assert result.success is True
        assert result.simple_english.deadline is None
        assert result.simple_english.fees is None
        assert result.simple_marathi.deadline is None

    def test_none_data_returns_error(self):
        """Passing None data should return a failure result."""
        result = simplify_notice(extracted_data=None)
        assert result.success is False
        assert "No structured data" in result.error

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_returns_error(self):
        """Missing API key should return an error without calling the API."""
        # Remove env var completely
        os.environ.pop("OPENAI_API_KEY", None)
        result = simplify_notice(
            extracted_data=SAMPLE_STRUCTURED_DATA,
            api_key=None,
        )
        assert result.success is False
        assert "OPENAI_API_KEY" in result.error or "GROQ_API_KEY" in result.error or "API" in result.error

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-12345"})
    @patch("openai.OpenAI")
    def test_api_failure_handled_gracefully(self, mock_openai_class):
        """API exceptions should be caught and returned as errors."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = Exception("API rate limit exceeded")
        mock_openai_class.return_value = mock_client

        result = simplify_notice(
            extracted_data=SAMPLE_STRUCTURED_DATA,
            api_key="test-key-12345",
        )

        assert result.success is False
        assert "rate limit" in result.error.lower()


class TestSimplificationSchemas:
    """Test the Pydantic schemas directly."""

    def test_english_schema_required_fields(self):
        """English schema should enforce required fields."""
        data = {
            "what_is_this_notice_about": "Test notice",
            "who_is_it_for": "All students",
            "what_do_i_need_to_do": "Nothing",
        }
        obj = SimplifiedEnglish(**data)
        assert obj.what_is_this_notice_about == "Test notice"
        assert obj.deadline is None
        assert obj.fees is None

    def test_marathi_schema_with_aliases(self):
        """Marathi schema should accept aliased field names."""
        data = {
            "हा_नोटीस_कशाबद्दल_आहे": "चाचणी नोटीस",
            "कोणासाठी_आहे": "सर्व विद्यार्थी",
            "मला_काय_करावे_लागेल": "काहीही नाही",
        }
        obj = SimplifiedMarathi(**data)
        assert obj.notice_about == "चाचणी नोटीस"
        assert obj.deadline is None

    def test_simplification_result_model(self):
        """SimplificationResult should validate correctly."""
        result = SimplificationResult(
            success=True,
            simple_english=SimplifiedEnglish(
                what_is_this_notice_about="Test",
                who_is_it_for="Students",
                what_do_i_need_to_do="Nothing",
            ),
            simple_marathi=None,
            model_used="gpt-5.6-luna",
        )
        assert result.success is True
        assert result.simple_english is not None
        assert result.simple_marathi is None
