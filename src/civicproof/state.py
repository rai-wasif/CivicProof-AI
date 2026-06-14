from __future__ import annotations

from typing import Any, Optional

from typing_extensions import TypedDict


class CivicState(TypedDict, total=False):
    case_id: str
    created_at: str

    user_input: str
    image_path: Optional[str]
    image_filename: Optional[str]
    input_type: str

    citizen_name: str
    location: Optional[str]
    landmark: Optional[str]
    date_time: Optional[str]
    language: str
    complaint_style: str

    image_summary: str
    image_evidence_notes: list[str]
    vision_issue_category: str
    vision_urgency_level: str
    vision_confidence: float
    extracted_problem: str
    detected_entities: dict[str, Any]
    llm_summary: str

    issue_category: str
    urgency_level: str
    evidence_score: int
    missing_details: list[str]
    followup_questions: list[str]

    department: str
    complaint_draft: str
    followup_message: str
    escalation_message: str

    needs_human_approval: bool
    user_approved: Optional[bool]
    case_status: str
    saved_case_id: Optional[str]
    node_trace: list[str]
