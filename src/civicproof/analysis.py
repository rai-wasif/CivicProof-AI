from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .constants import ISSUE_BASE_URGENCY, ISSUE_DEPARTMENTS, ISSUE_KEYWORDS, URGENCY_KEYWORDS


def normalize_text(text: str | None) -> str:
    return " ".join((text or "").strip().split())


def detect_input_type(user_input: str | None, image_path: str | None) -> str:
    has_text = bool(normalize_text(user_input))
    has_image = bool(image_path)
    if has_text and has_image:
        return "mixed"
    if has_image:
        return "image"
    return "text"


def extract_details(
    text: str | None,
    location: str | None = None,
    landmark: str | None = None,
    date_time: str | None = None,
) -> dict[str, str | None]:
    text_value = normalize_text(text)
    found_location = normalize_text(location)
    found_landmark = normalize_text(landmark)

    if not found_location and text_value:
        match = re.search(
            r"\b(?:near|at|in|outside|opposite|behind|around)\s+([A-Za-z0-9 ,.'/-]{3,90})",
            text_value,
            flags=re.IGNORECASE,
        )
        if match:
            found_location = match.group(1).strip(" .,")

    if not found_landmark and text_value:
        match = re.search(
            r"\b(?:landmark|nearby|close to)\s+([A-Za-z0-9 ,.'/-]{3,80})",
            text_value,
            flags=re.IGNORECASE,
        )
        if match:
            found_landmark = match.group(1).strip(" .,")

    clean_date_time = normalize_text(date_time)
    return {
        "location": found_location or None,
        "landmark": found_landmark or None,
        "date_time": clean_date_time or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def classify_issue(text: str | None, image_summary: str | None = None, llm_category: str | None = None) -> str:
    if llm_category in ISSUE_KEYWORDS:
        return llm_category

    combined = f"{normalize_text(text)} {normalize_text(image_summary)}".lower()
    if not combined.strip():
        return "Unknown"

    scores: dict[str, int] = {}
    for issue, keywords in ISSUE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in combined:
                score += 2 if " " in keyword else 1
        scores[issue] = score

    best_issue, best_score = max(scores.items(), key=lambda item: item[1])
    return best_issue if best_score > 0 else "Unknown"


def estimate_urgency(issue_category: str, text: str | None, image_summary: str | None = None) -> str:
    combined = f"{normalize_text(text)} {normalize_text(image_summary)}".lower()
    for urgency, keywords in URGENCY_KEYWORDS.items():
        if any(keyword in combined for keyword in keywords):
            return urgency
    return ISSUE_BASE_URGENCY.get(issue_category, "Low")


def score_evidence(state: dict[str, Any]) -> tuple[int, list[str]]:
    score = 15
    missing: list[str] = []

    user_input = normalize_text(state.get("user_input"))
    if len(user_input) >= 20:
        score += 15
    else:
        missing.append("Clear written description")

    if state.get("image_path"):
        score += 15
    else:
        missing.append("Photo evidence")

    if state.get("location"):
        score += 20
    else:
        missing.append("Exact street, area, or GPS location")

    if state.get("landmark"):
        score += 10
    else:
        missing.append("Nearby landmark")

    if state.get("date_time"):
        score += 10
    else:
        missing.append("Date and time")

    if state.get("issue_category") and state.get("issue_category") != "Unknown":
        score += 15
    else:
        missing.append("Recognizable issue category")

    if state.get("urgency_level") == "High":
        score += 5

    return min(score, 100), missing


def route_department(issue_category: str) -> str:
    return ISSUE_DEPARTMENTS.get(issue_category, ISSUE_DEPARTMENTS["Unknown"])


def build_followup_questions(missing_details: list[str]) -> list[str]:
    prompts = {
        "Clear written description": "Please add one sentence describing what happened and how residents are affected.",
        "Photo evidence": "Please attach a clear photo that shows the civic issue and nearby surroundings.",
        "Exact street, area, or GPS location": "Please add the street name, area, or GPS location.",
        "Nearby landmark": "Please add a nearby landmark such as a shop, school, mosque, park, or chowk.",
        "Date and time": "Please add when you observed the issue.",
        "Recognizable issue category": "Please clarify whether this is garbage, sewage, road damage, streetlight, or water leakage.",
    }
    return [prompts[item] for item in missing_details if item in prompts]


def build_complaint_draft(state: dict[str, Any]) -> str:
    category = state.get("issue_category", "civic issue")
    location = state.get("location") or "[exact location]"
    landmark = state.get("landmark") or "[nearby landmark]"
    department = state.get("department") or route_department(category)
    urgency = state.get("urgency_level", "Medium")
    citizen_name = state.get("citizen_name") or "[Your Name]"
    description = normalize_text(state.get("user_input")) or f"A {category.lower()} issue has been observed."
    language = state.get("language") or "English"
    style = state.get("complaint_style") or "Formal government"

    if style == "Short WhatsApp":
        if language == "Roman Urdu":
            return (
                f"Assalam o Alaikum. {location} ke qareeb {landmark} par {category} ka masla hai. "
                f"Is se residents ko mushkil ho rahi hai. Barah-e-karam {department} is maslay ko jaldi check kare. "
                f"Urgency: {urgency}. Shukriya, {citizen_name}."
            )
        return (
            f"Please check a {category.lower()} issue near {landmark}, {location}. "
            f"It is affecting residents and needs {urgency.lower()} priority action by {department}. "
            f"Regards, {citizen_name}."
        )

    if style == "Escalation":
        return (
            f"Subject: Escalation Request for Unresolved {category} Complaint\n\n"
            "Respected Sir/Madam,\n\n"
            f"I am requesting escalation of an unresolved {category.lower()} issue at {location}, near {landmark}. "
            f"The matter was reported with evidence and remains a public inconvenience. Current urgency is marked as {urgency}. "
            f"Original description: {description}\n\n"
            "Kindly assign the responsible field team and share an update with the complainant.\n\n"
            f"Regards,\n{citizen_name}"
        )

    if language == "Roman Urdu":
        return (
            f"Subject: {category} ke maslay ke hawalay se darkhwast\n\n"
            "Respected Sir/Madam,\n\n"
            f"Main aap ki tawajjo {location}, near {landmark}, par mojood {category.lower()} ke maslay ki taraf dilana chahta/chahti hoon. "
            f"Maslay ki tafseel yeh hai: {description}. Is wajah se ilaqay ke residents ko pareshani ka samna hai. "
            f"Evidence score {state.get('evidence_score', 0)}/100 hai aur urgency {urgency} mark ki gayi hai.\n\n"
            f"Barah-e-karam {department} is complaint ka inspection kar ke jald az jald masla hal kare.\n\n"
            f"Regards,\n{citizen_name}"
        )

    if language == "Urdu script":
        return (
            "Subject: Formal complaint draft in Urdu script\n\n"
            "Urdu script generation is available when an LLM provider is configured. "
            "Until then, CivicProof has prepared the following formal English draft.\n\n"
            + build_complaint_draft({**state, "language": "English"})
        )

    return (
        f"Subject: Complaint Regarding {category} at {location}\n\n"
        "Respected Sir/Madam,\n\n"
        f"I would like to report a {category.lower()} issue at {location}, near {landmark}. "
        f"{description} This issue is causing inconvenience for residents and requires {urgency.lower()} priority inspection. "
        f"The complaint has been routed to {department}. Evidence quality is currently {state.get('evidence_score', 0)}/100.\n\n"
        "Kindly inspect the site and resolve the issue as soon as possible. Photo or text evidence can be provided for verification.\n\n"
        f"Regards,\n{citizen_name}"
    )


def build_followup_message(state: dict[str, Any]) -> str:
    category = state.get("issue_category", "civic issue")
    location = state.get("location") or "[location]"
    department = state.get("department") or route_department(category)
    return (
        f"Follow-up: The {category.lower()} complaint at {location} was submitted for {department}. "
        "Please share inspection status, assigned officer details, and expected resolution time."
    )


def build_escalation_message(state: dict[str, Any]) -> str:
    category = state.get("issue_category", "civic issue")
    location = state.get("location") or "[location]"
    return (
        f"Escalation: This {category.lower()} issue at {location} remains unresolved after the expected follow-up period. "
        "Please escalate it to the responsible supervisor and provide a written update."
    )
