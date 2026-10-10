"""
Language Detection Module
Detects the language of extracted text using script analysis and ML models.
"""

from src.language.detector import detect_language, LanguageResult

__all__ = ["detect_language", "LanguageResult"]
