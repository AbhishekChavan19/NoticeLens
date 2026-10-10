"""
Pydantic Schemas for Notice Simplification (Phase 6)

Defines the structured output format for student-friendly notice explanations
in both English and Simple Marathi.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SimplifiedEnglish(BaseModel):
    """Student-friendly English explanation of a college notice."""

    what_is_this_notice_about: str = Field(
        ...,
        description="Simple, concise explanation of what the notice is about.",
    )
    who_is_it_for: str = Field(
        ...,
        description="Target audience in plain language (e.g., 'All Final Year B.Tech students').",
    )
    what_do_i_need_to_do: str = Field(
        ...,
        description="Clear action steps the student needs to take. 'No action needed.' if none.",
    )
    deadline: Optional[str] = Field(
        default=None,
        description="Final deadline. Exact date preserved from extracted data. None if absent.",
    )
    important_dates: Optional[str] = Field(
        default=None,
        description="All key dates/schedules. None if absent.",
    )
    documents_required: Optional[str] = Field(
        default=None,
        description="List of required documents. None if absent.",
    )
    fees: Optional[str] = Field(
        default=None,
        description="Fee amounts or payment details. None if absent.",
    )
    eligibility: Optional[str] = Field(
        default=None,
        description="Who is eligible. None if absent.",
    )
    important_note: Optional[str] = Field(
        default=None,
        description="Any critical warnings or extra context. None if absent.",
    )


class SimplifiedMarathi(BaseModel):
    """Student-friendly Marathi explanation of a college notice."""

    notice_about: str = Field(
        ...,
        alias="हा_नोटीस_कशाबद्दल_आहे",
        description="हा नोटीस कशाबद्दल आहे? — Simple Marathi explanation.",
    )
    who_is_it_for: str = Field(
        ...,
        alias="कोणासाठी_आहे",
        description="कोणासाठी आहे? — Target audience in simple Marathi.",
    )
    what_to_do: str = Field(
        ...,
        alias="मला_काय_करावे_लागेल",
        description="मला काय करावे लागेल? — Action steps in Marathi.",
    )
    deadline: Optional[str] = Field(
        default=None,
        alias="अंतिम_तारीख",
        description="अंतिम तारीख — Exact deadline. None if absent.",
    )
    important_dates: Optional[str] = Field(
        default=None,
        alias="महत्त्वाच्या_तारखा",
        description="महत्त्वाच्या तारखा — Key dates. None if absent.",
    )
    documents_required: Optional[str] = Field(
        default=None,
        alias="आवश्यक_कागदपत्रे",
        description="आवश्यक कागदपत्रे — Required documents. None if absent.",
    )
    fees: Optional[str] = Field(
        default=None,
        alias="फी",
        description="फी — Fee amounts. None if absent.",
    )
    eligibility: Optional[str] = Field(
        default=None,
        alias="पात्रता",
        description="पात्रता — Eligibility. None if absent.",
    )
    important_note: Optional[str] = Field(
        default=None,
        alias="महत्त्वाची_सूचना",
        description="महत्त्वाची सूचना — Important note. None if absent.",
    )

    model_config = ConfigDict(populate_by_name=True)


class SimplificationResult(BaseModel):
    """Wrapper returned by the simplifier containing both language outputs."""

    success: bool = Field(..., description="Whether simplification succeeded")
    simple_english: Optional[SimplifiedEnglish] = Field(
        default=None, description="Student-friendly English explanation"
    )
    simple_marathi: Optional[SimplifiedMarathi] = Field(
        default=None, description="Student-friendly Marathi explanation"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    model_used: str = Field(
        default="gpt-5.6-luna", description="Model used for simplification"
    )
