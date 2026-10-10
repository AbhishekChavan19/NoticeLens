"""
NoticeLens FastAPI Backend
Exposes the full NLP pipeline as a REST API for the Android app.

Endpoints:
  GET  /              - Status
  GET  /health        - Health check
  POST /api/v1/process - Main pipeline: PDF/image/text -> structured extraction + simplification
"""
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Phase 1: PDF / OCR text extraction
from src.pdf.extractor import extract_from_pdf

# Phase 3: Language detection
from src.language.detector import detect_language, LanguageResult

# Phase 4: Classification
from src.classification.predictor import predict_notice_category

# Phase 5 & 6: LLM extraction and simplification
from src.extraction.extractor import extract_structured_information
from src.simplification.simplifier import simplify_notice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NoticeLens API",
    description="Multilingual College Notice Understanding System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessResult(BaseModel):
    success: bool
    error: Optional[str] = None
    extracted_text: Optional[str] = None
    language: Optional[str] = None
    language_confidence: Optional[float] = None
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    structured_data: Optional[dict] = None
    simple_english: Optional[dict] = None
    simple_marathi: Optional[dict] = None
    model_used: Optional[str] = None


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "NoticeLens API is running", "version": "1.0.0"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.post("/api/v1/process", response_model=ProcessResult)
async def process_notice(
    file: Optional[UploadFile] = File(default=None),
    text_input: Optional[str] = Form(default=None),
    provider: str = Form(default="groq"),
    api_key: Optional[str] = Form(default=None),
):
    """
    Main pipeline endpoint. Accepts a PDF, image, or raw text notice.
    Returns language, category, structured extraction, and simplified summaries.
    """
    extracted_text = None

    # ── Phase 1: Extract text ────────────────────────────────────────────────
    if file is not None:
        file_bytes = await file.read()
        filename = (file.filename or "upload").lower()
        try:
            suffix = Path(filename).suffix or ".bin"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            result = extract_from_pdf(file_bytes)   # Works for PDF and images
            os.unlink(tmp_path)
            extracted_text = result.extracted_text
        except Exception as e:
            return ProcessResult(success=False, error=f"Text extraction failed: {str(e)}")

    elif text_input:
        extracted_text = text_input.strip()
    else:
        return ProcessResult(success=False, error="Provide a file (PDF/image) or text_input.")

    if not extracted_text or len(extracted_text.strip()) < 10:
        return ProcessResult(success=False, error="Could not extract meaningful text.", extracted_text=extracted_text)

    logger.info(f"Extracted {len(extracted_text)} characters.")

    # ── Phase 3: Language detection ──────────────────────────────────────────
    try:
        lang_result: LanguageResult = detect_language(extracted_text)
        language = lang_result.language
        language_confidence = float(lang_result.confidence)
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        language, language_confidence = "English", 0.0

    # ── Phase 4: Classification ──────────────────────────────────────────────
    try:
        cls_result = predict_notice_category(extracted_text)
        category = cls_result.get("category", "General")
        category_confidence = float(cls_result.get("confidence", 0.0))
    except Exception as e:
        logger.warning(f"Classification failed: {e}")
        category, category_confidence = "General", 0.0

    logger.info(f"Language: {language} ({language_confidence:.2f}) | Category: {category} ({category_confidence:.2f})")

    # ── Phase 5: LLM Structured Extraction ──────────────────────────────────
    try:
        ext_result = extract_structured_information(
            text=extracted_text,
            category=category,
            language=language,
            provider=provider,
            api_key=api_key or None,
        )
    except Exception as e:
        return ProcessResult(
            success=False, error=f"Extraction error: {str(e)}",
            extracted_text=extracted_text, language=language,
            language_confidence=language_confidence,
            category=category, category_confidence=category_confidence,
        )

    if not ext_result.success or not ext_result.data:
        return ProcessResult(
            success=False,
            error=ext_result.error or "LLM extraction failed",
            extracted_text=extracted_text,
            language=language, language_confidence=language_confidence,
            category=category, category_confidence=category_confidence,
        )

    # ── Phase 6: Simplification ──────────────────────────────────────────────
    simple_english, simple_marathi = None, None
    try:
        simp_result = simplify_notice(
            extracted_data=ext_result.data,
            provider=provider,
            api_key=api_key or None,
        )
        if simp_result.success:
            if simp_result.simple_english:
                simple_english = simp_result.simple_english.model_dump()
            if simp_result.simple_marathi:
                marathi_by_alias = simp_result.simple_marathi.model_dump(by_alias=True)
                marathi_by_name = simp_result.simple_marathi.model_dump(by_alias=False)
                simple_marathi = {**marathi_by_name, **marathi_by_alias}
    except Exception as e:
        logger.warning(f"Simplification failed: {e}")

    return ProcessResult(
        success=True,
        extracted_text=extracted_text,
        language=language, language_confidence=language_confidence,
        category=category, category_confidence=category_confidence,
        structured_data=ext_result.data.model_dump(),
        simple_english=simple_english,
        simple_marathi=simple_marathi,
        model_used=ext_result.model_used,
    )
