from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .analysis import (
    build_complaint_draft,
    build_escalation_message,
    build_followup_message,
    build_followup_questions,
    classify_issue,
    detect_input_type,
    estimate_urgency,
    extract_details,
    normalize_text,
    route_department,
    score_evidence,
)
from .image_tools import analyze_image
from .llm import GeminiVisionClient, OptionalLLMClient
from .state import CivicState


def _trace(state: CivicState, node_name: str) -> list[str]:
    return [*state.get("node_trace", []), node_name]


def receive_complaint(state: CivicState) -> CivicState:
    details = extract_details(
        state.get("user_input"),
        state.get("location"),
        state.get("landmark"),
        state.get("date_time"),
    )
    return {
        "case_id": state.get("case_id") or uuid4().hex,
        "created_at": state.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        "user_input": normalize_text(state.get("user_input")),
        "location": details["location"],
        "landmark": details["landmark"],
        "date_time": details["date_time"],
        "language": state.get("language") or "English",
        "complaint_style": state.get("complaint_style") or "Formal government",
        "citizen_name": normalize_text(state.get("citizen_name")) or "Citizen",
        "case_status": "analysis_started",
        "node_trace": _trace(state, "receive_complaint"),
    }


def detect_input_type_node(state: CivicState) -> CivicState:
    return {
        "input_type": detect_input_type(state.get("user_input"), state.get("image_path")),
        "node_trace": _trace(state, "detect_input_type"),
    }


def image_evidence_analyzer(state: CivicState) -> CivicState:
    summary, notes = analyze_image(state.get("image_path"))
    updates: CivicState = {
        "image_summary": summary,
        "image_evidence_notes": notes,
        "node_trace": _trace(state, "image_evidence_analyzer"),
    }

    if state.get("image_path"):
        vision_data = GeminiVisionClient.from_env().analyze_civic_image(
            state["image_path"],
            state.get("user_input"),
        )
        if vision_data:
            visible_evidence = vision_data.get("visible_evidence") or []
            missing_details = vision_data.get("missing_details") or []
            if not isinstance(visible_evidence, list):
                visible_evidence = [str(visible_evidence)]
            if not isinstance(missing_details, list):
                missing_details = [str(missing_details)]

            vision_summary = str(vision_data.get("summary") or "").strip()
            if vision_summary:
                updates["image_summary"] = f"{summary} Gemini Vision: {vision_summary}".strip()
            updates["image_evidence_notes"] = [
                *notes,
                *[f"Visible: {item}" for item in visible_evidence],
                *[f"Missing: {item}" for item in missing_details],
            ]
            updates["vision_issue_category"] = str(vision_data.get("issue_category") or "Unknown")
            updates["vision_urgency_level"] = str(vision_data.get("urgency_level") or "")
            try:
                updates["vision_confidence"] = float(vision_data.get("confidence") or 0)
            except (TypeError, ValueError):
                updates["vision_confidence"] = 0.0

            category = updates.get("vision_issue_category")
            if category in {"Garbage", "Sewage", "Road damage", "Streetlight", "Water leakage", "Unknown"}:
                updates["issue_category"] = category
            if updates.get("vision_urgency_level") in {"Low", "Medium", "High"}:
                updates["urgency_level"] = updates["vision_urgency_level"]

    return updates


def text_issue_analyzer(state: CivicState) -> CivicState:
    text = state.get("user_input", "")
    summary = ""
    detected_entities: dict[str, str] = {}

    llm = OptionalLLMClient.from_env()
    if llm.configured and text:
        llm_data = llm.generate_json(
            "Analyze this civic complaint. Return JSON with keys summary, issue_category, location, landmark, risk_notes. "
            f"Complaint: {text}"
        )
        if llm_data:
            summary = str(llm_data.get("summary") or "")
            detected_entities = {key: str(value) for key, value in llm_data.items() if value is not None}

    if not summary:
        summary = text or state.get("image_summary") or "Complaint evidence received for civic issue analysis."

    updates: CivicState = {
        "extracted_problem": summary,
        "detected_entities": detected_entities,
        "llm_summary": summary if detected_entities else "",
        "node_trace": _trace(state, "text_issue_analyzer"),
    }

    if detected_entities.get("location") and not state.get("location"):
        updates["location"] = detected_entities["location"]
    if detected_entities.get("landmark") and not state.get("landmark"):
        updates["landmark"] = detected_entities["landmark"]
    if detected_entities.get("issue_category"):
        updates["issue_category"] = detected_entities["issue_category"]
    return updates


def classify_issue_node(state: CivicState) -> CivicState:
    if state.get("vision_issue_category") in {"Garbage", "Sewage", "Road damage", "Streetlight", "Water leakage"}:
        return {
            "issue_category": state["vision_issue_category"],
            "node_trace": _trace(state, "classify_issue"),
        }
    category = classify_issue(
        state.get("user_input"),
        state.get("image_summary"),
        state.get("issue_category"),
    )
    return {"issue_category": category, "node_trace": _trace(state, "classify_issue")}


def check_urgency(state: CivicState) -> CivicState:
    if state.get("vision_urgency_level") in {"Low", "Medium", "High"}:
        return {
            "urgency_level": state["vision_urgency_level"],
            "node_trace": _trace(state, "check_urgency"),
        }
    return {
        "urgency_level": estimate_urgency(state.get("issue_category", "Unknown"), state.get("user_input"), state.get("image_summary")),
        "node_trace": _trace(state, "check_urgency"),
    }


def check_evidence_quality(state: CivicState) -> CivicState:
    score, missing = score_evidence(state)
    return {
        "evidence_score": score,
        "missing_details": missing,
        "node_trace": _trace(state, "check_evidence_quality"),
    }


def ask_followup_questions(state: CivicState) -> CivicState:
    return {
        "followup_questions": build_followup_questions(state.get("missing_details", [])),
        "case_status": "needs_more_evidence",
        "node_trace": _trace(state, "ask_followup_questions"),
    }


def route_department_node(state: CivicState) -> CivicState:
    return {
        "department": route_department(state.get("issue_category", "Unknown")),
        "node_trace": _trace(state, "route_department"),
    }


def generate_complaint_draft(state: CivicState) -> CivicState:
    base_state = dict(state)
    base_state["department"] = state.get("department") or route_department(state.get("issue_category", "Unknown"))
    draft = None

    llm = OptionalLLMClient.from_env()
    if llm.configured:
        draft = llm.generate_text(
            "Write a formal civic complaint using the provided facts. Keep it concise and do not invent facts.\n"
            f"Facts: {base_state}"
        )

    return {
        "department": base_state["department"],
        "complaint_draft": draft or build_complaint_draft(base_state),
        "node_trace": _trace(state, "generate_complaint_draft"),
    }


def human_approval(state: CivicState) -> CivicState:
    return {
        "needs_human_approval": True,
        "user_approved": None,
        "case_status": "draft_pending_approval",
        "node_trace": _trace(state, "human_approval"),
    }


def create_followup_plan(state: CivicState) -> CivicState:
    return {
        "followup_message": build_followup_message(state),
        "escalation_message": build_escalation_message(state),
        "node_trace": _trace(state, "create_followup_plan"),
    }


def _route_by_input_type(state: CivicState) -> str:
    input_type = state.get("input_type", "text")
    if input_type in {"image", "mixed"}:
        return "image"
    return "text"


def _route_by_evidence(state: CivicState) -> str:
    return "complete" if int(state.get("evidence_score", 0)) >= 75 else "missing"


@lru_cache(maxsize=1)
def build_graph():
    workflow = StateGraph(CivicState)
    workflow.add_node("receive_complaint", receive_complaint)
    workflow.add_node("detect_input_type", detect_input_type_node)
    workflow.add_node("image_evidence_analyzer", image_evidence_analyzer)
    workflow.add_node("text_issue_analyzer", text_issue_analyzer)
    workflow.add_node("classify_issue", classify_issue_node)
    workflow.add_node("check_urgency", check_urgency)
    workflow.add_node("check_evidence_quality", check_evidence_quality)
    workflow.add_node("ask_followup_questions", ask_followup_questions)
    workflow.add_node("route_department", route_department_node)
    workflow.add_node("generate_complaint_draft", generate_complaint_draft)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("create_followup_plan", create_followup_plan)

    workflow.add_edge(START, "receive_complaint")
    workflow.add_edge("receive_complaint", "detect_input_type")
    workflow.add_conditional_edges(
        "detect_input_type",
        _route_by_input_type,
        {"image": "image_evidence_analyzer", "text": "text_issue_analyzer"},
    )
    workflow.add_edge("image_evidence_analyzer", "text_issue_analyzer")
    workflow.add_edge("text_issue_analyzer", "classify_issue")
    workflow.add_edge("classify_issue", "check_urgency")
    workflow.add_edge("check_urgency", "check_evidence_quality")
    workflow.add_conditional_edges(
        "check_evidence_quality",
        _route_by_evidence,
        {"complete": "route_department", "missing": "ask_followup_questions"},
    )
    workflow.add_edge("ask_followup_questions", "route_department")
    workflow.add_edge("route_department", "generate_complaint_draft")
    workflow.add_edge("generate_complaint_draft", "human_approval")
    workflow.add_edge("human_approval", "create_followup_plan")
    workflow.add_edge("create_followup_plan", END)
    return workflow.compile()


def analyze_complaint(
    *,
    user_input: str,
    image_path: str | None = None,
    image_filename: str | None = None,
    citizen_name: str = "Citizen",
    location: str | None = None,
    landmark: str | None = None,
    date_time: str | None = None,
    language: str = "English",
    complaint_style: str = "Formal government",
) -> CivicState:
    initial_state: CivicState = {
        "user_input": user_input,
        "image_path": image_path,
        "image_filename": image_filename,
        "citizen_name": citizen_name,
        "location": location,
        "landmark": landmark,
        "date_time": date_time,
        "language": language,
        "complaint_style": complaint_style,
    }
    return build_graph().invoke(initial_state)
