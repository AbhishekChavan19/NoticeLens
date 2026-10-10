"""
Structured Information Extraction Module for NoticeLens (Phase 5)

Uses LLM API (Groq or OpenAI) via Structured Outputs to extract
strict factual information from college notices into a validated schema.

Supports two providers:
- Groq (free tier, default): Uses OpenAI-compatible SDK with Groq base URL
- OpenAI: Uses OpenAI SDK directly

Adheres strictly to accuracy rules:
- Factual extraction only; zero hallucination of dates/deadlines/fees.
- Returns None / [] for absent fields.
- Preserves exact dates, numbers, and URLs.
- Validates LLM output via Pydantic schema before returning.
"""

import os
import json
import logging
from typing import Optional, Tuple

from dotenv import load_dotenv

from src.extraction.schemas import NoticeStructuredSchema, ExtractionResult

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Provider defaults
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

SYSTEM_PROMPT = """You are an expert NLP information extraction assistant for PCCOE college notices.
Your task is to extract factual, structured information from the provided notice text into JSON.

CRITICAL ACCURACY RULES:
1. Extract ONLY information explicitly present in the notice text.
2. NEVER invent or assume: dates, deadlines, fees, documents, eligibility criteria, links, or contact details.
3. If any field's information is absent from the notice text, return null or an empty list [].
4. Preserve exact dates, numbers, currency amounts, and URLs without altering or reformatting date structures.
5. Do NOT infer that a student must act unless the notice text explicitly mandates an action (action_required = true).
6. Do NOT summarize away important instructions or details.
7. Process English, Marathi, and mixed-language notices accurately.

Respond in valid JSON with these fields:
- title (string or null)
- category (string)
- language (string)
- what_is_this_about (string or null)
- target_audience (string or null)
- action_required (boolean or null)
- actions (list of strings)
- deadline (string or null)
- important_dates (list of strings)
- documents_required (list of strings)
- fees (string or null)
- eligibility (string or null)
- venue (string or null)
- portal_or_link (string or null)
- contact_information (string or null)
"""


def _get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple:
    """
    Create an OpenAI-compatible client for the specified provider.

    Returns:
        Tuple of (client, model_name, provider_name)
    """
    from openai import OpenAI

    if not provider:
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            if api_key.startswith("gsk_"):
                provider = "groq"
            else:
                provider = "openai"
        elif groq_key and groq_key != "your_groq_api_key_here":
            provider = os.getenv("LLM_PROVIDER", "groq")
        elif openai_key and openai_key != "your_openai_api_key_here":
            provider = "openai"
        else:
            provider = os.getenv("LLM_PROVIDER", "groq")

    if provider == "groq":
        effective_key = api_key or os.getenv("GROQ_API_KEY")
        if not effective_key or effective_key == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
                "and add it to your .env file."
            )
        client = OpenAI(api_key=effective_key, base_url=GROQ_BASE_URL)
        model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        return client, model, "Groq"

    else:  # openai
        effective_key = api_key or os.getenv("OPENAI_API_KEY")
        if not effective_key or effective_key == "your_openai_api_key_here":
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set it in your .env file."
            )
        client = OpenAI(api_key=effective_key)
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return client, model, "OpenAI"


def extract_structured_information(
    text: str,
    category: str = "General",
    language: str = "English",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> ExtractionResult:
    """
    Extract structured information from a college notice using LLM API.

    Args:
        text: Original extracted text of the notice.
        category: Predicted category label (from Phase 4).
        language: Detected language label (from Phase 3).
        api_key: API key (defaults to env var based on provider).
        model: Model name override (defaults to provider's default).
        provider: "groq" or "openai" (defaults to LLM_PROVIDER env var).

    Returns:
        ExtractionResult containing structured NoticeStructuredSchema data,
        original_text, success flag, and error details (if any).
    """
    effective_provider = provider
    effective_model = model or (
        DEFAULT_GROQ_MODEL if (effective_provider or os.getenv("LLM_PROVIDER")) == "groq" else DEFAULT_OPENAI_MODEL
    )

    if not text or not text.strip():
        return ExtractionResult(
            success=False,
            data=None,
            original_text=text or "",
            error="Input notice text is empty.",
            model_used=effective_model,
        )

    try:
        client, resolved_model, provider_name = _get_llm_client(
            provider=effective_provider, api_key=api_key
        )
        if model:
            resolved_model = model

        user_prompt = (
            f"Notice Category: {category}\n"
            f"Notice Language: {language}\n\n"
            f"Notice Text:\n\"\"\"\n{text}\n\"\"\""
        )

        parsed_data = None

        if provider_name == "OpenAI":
            try:
                completion = client.beta.chat.completions.parse(
                    model=resolved_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=NoticeStructuredSchema,
                    temperature=0.1,
                )
                parsed_data = completion.choices[0].message.parsed
            except (AttributeError, TypeError):
                parsed_data = None

        if parsed_data is None:
            completion = client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=700,
            )
            raw_json = completion.choices[0].message.content
            if not isinstance(raw_json, str):
                raw_json = str(raw_json)
            parsed_data = NoticeStructuredSchema.model_validate_json(raw_json)

        # Ensure category & language match inputs if LLM omitted them
        if not parsed_data.category:
            parsed_data.category = category
        if not parsed_data.language:
            parsed_data.language = language

        logger.info(f"Successfully extracted structured information using {provider_name}/{resolved_model}")
        return ExtractionResult(
            success=True,
            data=parsed_data,
            original_text=text,
            error=None,
            model_used=f"{provider_name}/{resolved_model}",
        )

    except ValueError as ve:
        # API key not configured
        logger.error(str(ve))
        return ExtractionResult(
            success=False,
            data=None,
            original_text=text,
            error=str(ve),
            model_used=effective_model,
        )

    except Exception as e:
        err_str = f"LLM extraction failed ({effective_provider}): {str(e)}"
        logger.error(err_str)
        return ExtractionResult(
            success=False,
            data=None,
            original_text=text,
            error=err_str,
            model_used=effective_model,
        )

