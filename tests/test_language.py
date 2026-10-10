"""
Tests for the Language Detection Module (Phase 3)

Run with:
    python -m pytest tests/test_language.py -v
"""

import pytest
from src.language.detector import detect_language, LanguageResult, MIXED_THRESHOLD, MIN_CHARS_FOR_DETECTION

# ---------------------------------------------------------------------------
# Sample Test Data
# ---------------------------------------------------------------------------

ENGLISH_NOTICE = """
PIMPRI CHINCHWAD COLLEGE OF ENGINEERING
NOTICE - EXAMINATION DEPARTMENT
All final year B.Tech students are hereby informed that the end semester examinations
for Academic Year 2024-25 will commence from 15th May 2025.
Detailed timetable and seating arrangement will be published on the college website.
Fees must be deposited before 10th May 2025.
"""

MARATHI_NOTICE = """
पिंपरी चिंचवड अभियांत्रिकी महाविद्यालय, निगडी, पुणे.
सूचना - परीक्षा विभाग
सर्व प्रथम वर्ष आणि द्वितीय वर्ष विद्यार्थ्यांसाठी कळविण्यात येते की
द्वितीय सत्र परीक्षा २०२५ दिनांक २० मे २०२५ पासून सुरू होत आहेत.
सर्व विद्यार्थ्यांनी आपले परीक्षा अर्ज मुदतीत भरावेत.
काही अडचण असल्यास परीक्षा कक्षाशी संपर्क साधावा.
"""

# Marathi notice containing a few English technical terms (should still classify as Marathi)
MARATHI_WITH_TECHNICAL_TERMS = """
पिंपरी चिंचवड अभियांत्रिकी महाविद्यालय, निगडी, पुणे.
सूचना: सर्व Computer Engineering आणि Information Technology विभागातील विद्यार्थ्यांना
कळविण्यात येते की AI and Machine Learning Workshop चे आयोजन करण्यात आले आहे.
उपस्थिती सर्व विद्यार्थ्यांसाठी अनिवार्य आहे. गैरहजर राहणाऱ्या विद्यार्थ्यांवर
नियमानुसार कारवाई करण्यात येईल.
दिनांक: २५ मार्च २०२५.
वेळ: सकाळी १०.०० वाजता. हॉल क्रमांक ३०२.
अधिक माहितीसाठी संबंधित विभाग प्रमुंशी संपर्क साधावा.
"""

BILINGUAL_NOTICE = """
PIMPRI CHINCHWAD COLLEGE OF ENGINEERING
NOTICE / सूचना
All students must pay their college tuition fees by 30th April 2025.
Late fine of Rs. 100 per day will be applicable.
सर्व विद्यार्थ्यांनी त्यांची महाविद्यालयीन फी ३० एप्रिल २०२५ पर्यंत भरावी.
उशिरा फी भरल्यास दररोज १०० रुपये दंड आकारला जाईल.
Contact accounts department for any fee related queries.
खाते विभागाशी संपर्क साधावा.
"""

NUMBERS_AND_SYMBOLS_ONLY = "1234567890 !@#$%^&*() 2025/05/15"


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_english_notice_detection():
    """Test detection on a pure English notice."""
    result = detect_language(ENGLISH_NOTICE)
    assert isinstance(result, LanguageResult)
    assert result.language == "English"
    assert result.confidence > 0.7
    assert result.distribution["en"] > 0.8
    assert result.distribution["mr"] < 0.2


def test_marathi_notice_detection():
    """Test detection on a pure Marathi notice."""
    result = detect_language(MARATHI_NOTICE)
    assert isinstance(result, LanguageResult)
    assert result.language == "Marathi"
    assert result.confidence > 0.7
    assert result.distribution["mr"] > 0.8
    assert result.distribution["en"] < 0.2


def test_marathi_with_english_technical_terms():
    """
    Test that a Marathi notice containing a few English terms (e.g. 'Computer Engineering')
    is correctly classified as Marathi and NOT Mixed.
    """
    result = detect_language(MARATHI_WITH_TECHNICAL_TERMS)
    assert isinstance(result, LanguageResult)
    assert result.language == "Marathi"
    # Verify Devanagari ratio is above dominant threshold (70%) or Latin is below 30%
    assert result.distribution["en"] < MIXED_THRESHOLD


def test_bilingual_notice_detection():
    """Test detection on a notice containing significant English and Marathi text."""
    result = detect_language(BILINGUAL_NOTICE)
    assert isinstance(result, LanguageResult)
    assert result.language == "Mixed"
    assert result.distribution["en"] >= MIXED_THRESHOLD
    assert result.distribution["mr"] >= MIXED_THRESHOLD


def test_empty_input():
    """Test behavior with empty or whitespace string."""
    res_empty = detect_language("")
    assert res_empty.language == "Unknown"
    assert res_empty.confidence == 0.0

    res_spaces = detect_language("   \n\t  ")
    assert res_spaces.language == "Unknown"
    assert res_spaces.confidence == 0.0

    res_none = detect_language(None)
    assert res_none.language == "Unknown"
    assert res_none.confidence == 0.0


def test_too_short_text():
    """Test that text below MIN_CHARS_FOR_DETECTION returns Unknown."""
    result = detect_language("Notice 1")  # Only 6 alpha chars ('Notice')
    assert result.language == "Unknown"
    assert result.detection_method == "insufficient_text"


def test_numbers_only_text():
    """Test text containing only numbers and symbols."""
    result = detect_language(NUMBERS_AND_SYMBOLS_ONLY)
    assert result.language == "Unknown"
    assert result.script_analysis["total_alpha"] == 0


def test_script_analysis_data():
    """Test that script analysis dictionary contains expected fields."""
    result = detect_language(ENGLISH_NOTICE)
    sa = result.script_analysis
    assert "devanagari_count" in sa
    assert "latin_count" in sa
    assert "total_alpha" in sa
    assert "latin_ratio" in sa
    assert "devanagari_ratio" in sa
    assert sa["latin_count"] > 0
    assert sa["devanagari_count"] == 0
