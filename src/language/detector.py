"""
Language Detection Module for NoticeLens

Detects the language of notice text using a two-tier approach:
    1. Unicode script analysis (primary) — counts Devanagari vs Latin characters
    2. ML-based detection (secondary) — uses langdetect or fastText if available

This combination is especially reliable for English vs Marathi detection
because the two languages use entirely different writing scripts
(Latin vs Devanagari), making script analysis alone highly accurate.

The ML layer adds value for:
    - Confidence scoring
    - Distinguishing Devanagari languages (Marathi vs Hindi)
    - Handling edge cases and transliterated text

Usage:
    from src.language.detector import detect_language

    result = detect_language("This is a college notice about examinations.")
    print(result.language)       # "English"
    print(result.confidence)     # 0.97
    print(result.distribution)   # {"en": 0.97, "mr": 0.03}
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Both scripts must contribute at least this fraction of alphabetic characters
# for the text to be classified as "Mixed". A threshold of 0.35 means:
#   - 70% Devanagari + 30% Latin  =>  Marathi  (Latin < 35%)
#   - 50% Devanagari + 50% Latin  =>  Mixed    (both >= 35%)
#   - 75% Latin + 25% Devanagari  =>  English  (Devanagari < 35%)
#
# This prevents notices with English technical terms from being
# classified as "Mixed" when they are fundamentally Marathi (or vice versa).
MIXED_THRESHOLD = 0.35

# Minimum alphabetic characters needed for a reliable detection.
# Texts shorter than this return "Unknown".
MIN_CHARS_FOR_DETECTION = 10


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ScriptAnalysis:
    """Result of Unicode script character counting."""

    devanagari_count: int = 0
    latin_count: int = 0
    other_count: int = 0
    total_alpha: int = 0
    devanagari_ratio: float = 0.0
    latin_ratio: float = 0.0


@dataclass
class LanguageResult:
    """Complete language detection result."""

    language: str             # "English", "Marathi", "Mixed", "Unknown"
    confidence: float         # 0.0 to 1.0
    distribution: dict        # {"en": 0.8, "mr": 0.2}
    script_analysis: dict     # Raw script analysis details
    detection_method: str     # "script+langdetect", "script+fasttext", "script_only"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_language(text: str) -> LanguageResult:
    """
    Detect the language of a text string.

    Uses Unicode script analysis as the primary signal (Devanagari = Marathi,
    Latin = English) and ML-based detection (langdetect/fastText) for
    confidence scoring and edge-case handling.

    A notice is classified as "Mixed" only when BOTH scripts contribute
    at least 30% of the alphabetic characters. A few English technical
    terms in an otherwise Marathi notice will NOT trigger "Mixed".

    Args:
        text: The text to analyze.

    Returns:
        LanguageResult with language label, confidence, and distribution.
    """
    # Handle empty / None input
    if not text or not text.strip():
        return LanguageResult(
            language="Unknown",
            confidence=0.0,
            distribution={"en": 0.0, "mr": 0.0},
            script_analysis={},
            detection_method="none",
        )

    # --- Step 1: Script analysis (always available, primary signal) ---
    script = _analyze_script(text)

    # Too few alphabetic characters for reliable detection
    if script.total_alpha < MIN_CHARS_FOR_DETECTION:
        return LanguageResult(
            language="Unknown",
            confidence=0.0,
            distribution={"en": script.latin_ratio, "mr": script.devanagari_ratio},
            script_analysis=_script_to_dict(script),
            detection_method="insufficient_text",
        )

    # --- Step 2: ML-based detection (for confidence + edge cases) ---
    ml_result = _ml_detect(text)
    detection_method = ml_result.get("method", "script_only") if ml_result else "script_only"

    # --- Step 3: Classify based on script ratios + ML confirmation ---
    language, confidence = _classify(script, ml_result)

    # Build distribution
    distribution = {
        "en": round(script.latin_ratio, 4),
        "mr": round(script.devanagari_ratio, 4),
    }

    logger.info(
        f"Language detected: {language} (confidence={confidence:.2f}, "
        f"en={distribution['en']:.2f}, mr={distribution['mr']:.2f}, "
        f"method={detection_method})"
    )

    return LanguageResult(
        language=language,
        confidence=round(confidence, 4),
        distribution=distribution,
        script_analysis=_script_to_dict(script),
        detection_method=detection_method,
    )


# ---------------------------------------------------------------------------
# Script Analysis (Tier 1 — always available)
# ---------------------------------------------------------------------------

def _analyze_script(text: str) -> ScriptAnalysis:
    """
    Count Devanagari vs Latin alphabetic characters in the text.

    Only alphabetic characters are counted. Digits, punctuation,
    whitespace, and symbols are ignored — a Marathi notice with
    "2025" or "15/03" should not get inflated Latin counts from digits.

    Devanagari range: U+0900 to U+097F (covers Marathi, Hindi, Sanskrit)
    Latin range: ASCII a-z, A-Z
    """
    devanagari = 0
    latin = 0
    other = 0

    for char in text:
        if '\u0900' <= char <= '\u097F':
            # Devanagari script (Marathi, Hindi, Sanskrit, etc.)
            devanagari += 1
        elif char.isascii() and char.isalpha():
            # Latin script (English)
            latin += 1
        elif char.isalpha():
            # Other alphabetic scripts
            other += 1

    total = devanagari + latin + other

    return ScriptAnalysis(
        devanagari_count=devanagari,
        latin_count=latin,
        other_count=other,
        total_alpha=total,
        devanagari_ratio=devanagari / total if total > 0 else 0.0,
        latin_ratio=latin / total if total > 0 else 0.0,
    )


def _script_to_dict(script: ScriptAnalysis) -> dict:
    """Convert ScriptAnalysis to a plain dict for serialization."""
    return {
        "devanagari_count": script.devanagari_count,
        "latin_count": script.latin_count,
        "other_count": script.other_count,
        "total_alpha": script.total_alpha,
        "devanagari_ratio": round(script.devanagari_ratio, 4),
        "latin_ratio": round(script.latin_ratio, 4),
    }


# ---------------------------------------------------------------------------
# ML-Based Detection (Tier 2 — optional, enhances confidence)
# ---------------------------------------------------------------------------

def _ml_detect(text: str) -> Optional[dict]:
    """
    Run ML-based language detection using available library.

    Tries (in order):
        1. ftlangdetect (fastText wrapper)
        2. langdetect (Google's language-detection port, pure Python)

    Returns:
        dict with keys "lang", "score", "method" — or None if unavailable.
    """
    # --- Try fastText (ftlangdetect) ---
    result = _try_fasttext(text)
    if result is not None:
        return result

    # --- Try langdetect (pure Python fallback) ---
    result = _try_langdetect(text)
    if result is not None:
        return result

    # No ML library available
    logger.debug("No ML language detection library available; using script analysis only.")
    return None


def _try_fasttext(text: str) -> Optional[dict]:
    """Attempt detection using ftlangdetect (fastText wrapper)."""
    try:
        from ftlangdetect import detect as ft_detect

        # fastText needs single-line input
        clean = text.replace("\n", " ").strip()
        if not clean:
            return None

        result = ft_detect(clean, low_memory=True)
        return {
            "lang": result.get("lang", "unknown"),
            "score": result.get("score", 0.0),
            "method": "script+fasttext",
        }
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"fastText detection failed: {e}")
        return None


def _try_langdetect(text: str) -> Optional[dict]:
    """Attempt detection using langdetect (pure Python)."""
    try:
        from langdetect import detect_langs, DetectorFactory

        # Seed for reproducible results (langdetect is non-deterministic by default)
        DetectorFactory.seed = 0

        results = detect_langs(text)
        if not results:
            return None

        # Best prediction
        best = results[0]
        return {
            "lang": best.lang,
            "score": best.prob,
            "method": "script+langdetect",
            "all_langs": {r.lang: round(r.prob, 4) for r in results},
        }
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"langdetect failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Classification Logic
# ---------------------------------------------------------------------------

def _classify(
    script: ScriptAnalysis,
    ml_result: Optional[dict],
) -> tuple:
    """
    Determine final language label and confidence.

    Decision logic:
        1. If Devanagari >= 70% of alphabetic chars  ->  Marathi
        2. If Latin >= 70% of alphabetic chars        ->  English
        3. If both >= 30%                             ->  Mixed

    The 30% threshold prevents a Marathi notice with English technical
    terms (e.g., "Computer Science", "B.Tech") from being labeled "Mixed".

    Confidence is based on script dominance, optionally boosted/reduced
    by the ML model's agreement.

    Returns:
        (language_str, confidence_float)
    """
    dev_r = script.devanagari_ratio
    lat_r = script.latin_ratio
    dominant_threshold = 1.0 - MIXED_THRESHOLD  # 0.70

    # --- Determine language from script ratios ---
    if dev_r >= dominant_threshold:
        language = "Marathi"
        script_confidence = dev_r
    elif lat_r >= dominant_threshold:
        language = "English"
        script_confidence = lat_r
    elif dev_r >= MIXED_THRESHOLD and lat_r >= MIXED_THRESHOLD:
        language = "Mixed"
        # For Mixed, confidence reflects how clearly both are present
        # Higher when balanced (50/50), lower when lopsided (31/69)
        balance = 1.0 - abs(dev_r - lat_r)
        script_confidence = 0.5 + balance * 0.5  # Maps [0, 1] -> [0.5, 1.0]
    elif dev_r > lat_r:
        language = "Marathi"
        script_confidence = dev_r
    else:
        language = "English"
        script_confidence = max(lat_r, 0.5)

    # --- Adjust confidence with ML result (if available) ---
    if ml_result and ml_result.get("score"):
        ml_lang = ml_result["lang"]
        ml_score = ml_result["score"]

        # Check if ML agrees with script analysis
        ml_agrees = (
            (language == "English" and ml_lang == "en")
            or (language == "Marathi" and ml_lang in ("mr", "hi"))
            or (language == "Mixed")
        )

        if ml_agrees:
            # ML confirms — boost confidence slightly
            confidence = script_confidence * 0.7 + ml_score * 0.3
        else:
            # ML disagrees — reduce confidence slightly
            confidence = script_confidence * 0.8 + 0.1
    else:
        confidence = script_confidence

    # Clamp to [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    return language, confidence
