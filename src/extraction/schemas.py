"""
Pydantic Schemas for Structured LLM Information Extraction (Phase 5)

Defines the exact JSON schema required by NoticeLens for LLM extraction.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NoticeStructuredSchema(BaseModel):
    """
    Strict Pydantic schema for college notice information extraction.
    Adheres strictly to the NoticeLens accuracy rules:
    - Return None/[] for any absent fields.
    - Never fabricate dates, deadlines, fees, documents, or contacts.
    - Preserve exact dates, numbers, and URLs without reformatting.
    """

    title: Optional[str] = Field(
        default=None,
        description="Official title or header of the notice. None if not present."
    )
    category: str = Field(
        ...,
        description="Notice category (e.g. Examination, Academics, Admission, Scholarship, etc.)"
    )
    language: str = Field(
        ...,
        description="Primary language of the notice (English, Marathi, Mixed)"
    )
    what_is_this_about: Optional[str] = Field(
        default=None,
        description="Factual, concise summary of what the notice is about."
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Intended audience (e.g., Final Year B.Tech, FE Students, All Faculty)."
    )
    action_required: Optional[bool] = Field(
        default=None,
        description="True if students/readers must take specific actions, False/None if purely informational."
    )
    actions: List[str] = Field(
        default_factory=list,
        description="List of specific actions required from the target audience. Empty list if none."
    )
    deadline: Optional[str] = Field(
        default=None,
        description="Final deadline date or time (exact text preserved). None if absent."
    )
    important_dates: List[str] = Field(
        default_factory=list,
        description="List of all important dates or schedules mentioned. Empty list if none."
    )
    documents_required: List[str] = Field(
        default_factory=list,
        description="List of required documents, certificates, or forms. Empty list if none."
    )
    fees: Optional[str] = Field(
        default=None,
        description="Fee amounts, fine details, or payment instructions. None if absent."
    )
    eligibility: Optional[str] = Field(
        default=None,
        description="Eligibility criteria or qualifications required. None if absent."
    )
    venue: Optional[str] = Field(
        default=None,
        description="Location, hall number, or room where event/exam takes place. None if absent."
    )
    portal_or_link: Optional[str] = Field(
        default=None,
        description="URLs, websites, or online portals mentioned. None if absent."
    )
    contact_information: Optional[str] = Field(
        default=None,
        description="Contact persons, email addresses, phone numbers, or office departments. None if absent."
    )


class ExtractionResult(BaseModel):
    """
    Wrapper returned to the application containing structured output,
    original text, and execution metadata.
    """

    success: bool = Field(..., description="Whether LLM extraction succeeded without error")
    data: Optional[NoticeStructuredSchema] = Field(default=None, description="Extracted structured schema")
    original_text: str = Field(..., description="Original unedited notice text")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")
    model_used: str = Field(default="gpt-5.6-luna", description="Model architecture used for extraction")
