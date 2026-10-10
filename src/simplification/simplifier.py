"""
Notice Simplification Module for NoticeLens (Phase 6)

Uses LLM API (Groq or OpenAI) to convert structured extracted notice
information into simple, actionable student-friendly explanations in
English and Simple Marathi.

Rules:
- Uses ONLY information present in the structured JSON input.
- Never invents dates, deadlines, fees, documents, or any details.
- Returns None for absent fields rather than fabricating content.
- Keeps language simple, concise, and student-friendly.
"""

import os
import json
import logging
from typing import Optional

from dotenv import load_dotenv

from src.extraction.schemas import NoticeStructuredSchema
from src.extraction.extractor import _get_llm_client
from src.simplification.schemas import (
    SimplifiedEnglish,
    SimplifiedMarathi,
    SimplificationResult,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ENGLISH = """You are an intelligent, student-friendly assistant for college notices.
Your task is to summarize structured notice data into a clear, helpful, and easily understandable overview in English.

GUIDELINES:
1. WHAT IS THIS NOTICE ABOUT: Clearly explain the core purpose, subject matter, and importance of this notice in clear, accessible sentences.
2. WHO IS IT FOR: Name the specific target students/classes (e.g., "All Final Year Computer Dept students").
3. WHAT DO I NEED TO DO: Clear actionable steps or "No action required. For information only."
4. DEADLINE: Exact deadline date/time or "No deadline mentioned."
5. IMPORTANT DATES: Key dates in brief or "None."
6. DOCUMENTS REQUIRED: List documents or "No documents required."
7. FEES: Fee amount or "No fees mentioned (Free)."
8. ELIGIBILITY: Eligibility criteria or "Applicable to all mentioned students."
9. IMPORTANT NOTE: Important alerts, instructions or "Adhere to college guidelines."

Respond in valid JSON with these fields:
- what_is_this_notice_about (string)
- who_is_it_for (string)
- what_do_i_need_to_do (string)
- deadline (string or 'No deadline mentioned')
- important_dates (string or 'None')
- documents_required (string or 'No documents required')
- fees (string or 'No fees mentioned')
- eligibility (string or 'Applicable to all mentioned students')
- important_note (string or 'Adhere to college guidelines')
"""

SYSTEM_PROMPT_MARATHI = """तुम्ही कॉलेजच्या विद्यार्थ्यांसाठी उपयुक्त व मार्गदर्शक सहाय्यक आहात.
तुमचे काम structured कॉलेज नोटीस डेटा सोप्या, स्पष्ट आणि विद्यार्थी-अनुकूल मराठीमध्ये रूपांतरित करणे आहे.

मार्गदर्शक तत्त्वे:
1. हा नोटीस कशाबद्दल आहे: नोटीसचा मुख्य हेतू आणि महत्त्व सोप्या मराठीत स्पष्ट सांगा जेणेकरून वाचकाला पूर्ण माहिती समजेल.
2. कोणासाठी आहे: लक्ष्यित विद्यार्थी किंवा वर्ग स्पष्ट सांगा.
3. मला काय करावे लागेल: नेमकी कृती किंवा "कोणतीही कृती आवश्यक नाही. केवळ माहितीसाठी."
4. अंतिम तारीख: अंतिम तारीख किंवा "कोणतीही अंतिम तारीख नमूद केलेली नाही."
5. महत्त्वाच्या तारखा: तारखा किंवा "नाहीत."
6. आवश्यक कागदपत्रे: कागदपत्रांची यादी किंवा "कोणत्याही कागदपत्रांची आवश्यकता नाही."
7. फी: फीची रक्कम किंवा "कोणतीही फी नमूद केलेली नाही (मोफत)."
8. पात्रता: पात्रता निकष किंवा "सर्व संबंधित विद्यार्थ्यांसाठी लागू."
9. महत्त्वाची सूचना: महत्त्वाची सूचना किंवा "कॉलेजच्या नियमांचे पालन करा."

Respond in valid JSON with these exact fields:
- हा_नोटीस_कशाबद्दल_आहे (string)
- कोणासाठी_आहे (string)
- मला_काय_करावे_लागेल (string)
- अंतिम_तारीख (string)
- महत्त्वाच्या_तारखा (string)
- आवश्यक_कागदपत्रे (string)
- फी (string)
- पात्रता (string)
- महत्त्वाची_सूचना (string)
"""

def _build_input_json(data: NoticeStructuredSchema) -> str:
    """Serialise structured notice data to a compact JSON string for the LLM prompt."""
    return json.dumps(data.model_dump(), indent=2, ensure_ascii=False)


def _simplify_english(
    structured_json_str: str,
    client,
    model: str,
    provider_name: str = "Groq",
) -> SimplifiedEnglish:
    """Call LLM to produce a SimplifiedEnglish output."""
    user_prompt = (
        "Here is the structured notice data extracted from a college notice:\n\n"
        f"```json\n{structured_json_str}\n```\n\n"
        "Convert this into a simple, student-friendly English explanation."
    )

    if provider_name == "OpenAI":
        try:
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_ENGLISH},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SimplifiedEnglish,
                temperature=0.2,
            )
            return completion.choices[0].message.parsed
        except (AttributeError, TypeError):
            pass

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ENGLISH},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw_json = completion.choices[0].message.content
    if not isinstance(raw_json, str):
        raw_json = str(raw_json)
    return SimplifiedEnglish.model_validate_json(raw_json)


def _simplify_marathi(
    structured_json_str: str,
    client,
    model: str,
    provider_name: str = "Groq",
) -> SimplifiedMarathi:
    """Call LLM to produce a SimplifiedMarathi output."""
    user_prompt = (
        "खालील structured कॉलेज नोटीस डेटा आहे:\n\n"
        f"```json\n{structured_json_str}\n```\n\n"
        "हा डेटा सोप्या, विद्यार्थी-अनुकूल मराठीमध्ये रूपांतरित करा."
    )

    if provider_name == "OpenAI":
        try:
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_MARATHI},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SimplifiedMarathi,
                temperature=0.2,
            )
            return completion.choices[0].message.parsed
        except (AttributeError, TypeError):
            pass

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_MARATHI},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw_json = completion.choices[0].message.content
    if not isinstance(raw_json, str):
        raw_json = str(raw_json)
    return SimplifiedMarathi.model_validate_json(raw_json)


def simplify_notice(
    extracted_data: NoticeStructuredSchema,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> SimplificationResult:
    """
    Convert structured extraction output into student-friendly summaries.

    Args:
        extracted_data: Validated NoticeStructuredSchema from Phase 5.
        api_key: API key (defaults to env var based on provider).
        model: Model name override (defaults to provider's default).
        provider: "groq" or "openai" (defaults to LLM_PROVIDER env var).

    Returns:
        SimplificationResult containing both English and Marathi explanations.
    """
    effective_provider = provider

    if extracted_data is None:
        return SimplificationResult(
            success=False,
            error="No structured data provided for simplification.",
            model_used="N/A",
        )

    try:
        client, resolved_model, provider_name = _get_llm_client(
            provider=effective_provider, api_key=api_key
        )
        if model:
            resolved_model = model

        structured_json_str = _build_input_json(extracted_data)

        # Generate both outputs
        logger.info("Generating simplified English explanation...")
        english_result = _simplify_english(structured_json_str, client, resolved_model, provider_name)

        logger.info("Generating simplified Marathi explanation...")
        marathi_result = _simplify_marathi(structured_json_str, client, resolved_model, provider_name)

        display_model = f"{provider_name}/{resolved_model}"
        logger.info(f"Simplification completed successfully using {display_model}")
        return SimplificationResult(
            success=True,
            simple_english=english_result,
            simple_marathi=marathi_result,
            error=None,
            model_used=display_model,
        )

    except Exception as e:
        err_str = f"Simplification failed: {str(e)}"
        logger.error(err_str)
        return SimplificationResult(
            success=False, error=err_str, model_used="N/A"
        )
