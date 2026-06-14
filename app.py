from __future__ import annotations

import sys
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
from uuid import uuid4

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from civicproof.agent import analyze_complaint
from civicproof.config import DOCS_DIR, UPLOADS_DIR, ensure_directories
from civicproof.constants import SUPPORTED_LANGUAGES, SUPPORTED_STYLES
from civicproof.db import get_case, init_db, list_cases, save_case, update_case_status
from civicproof.llm import GeminiVisionClient, OptionalLLMClient
from civicproof.pdf_report import generate_case_pdf


st.set_page_config(page_title="CivicProof AI", page_icon="CP", layout="wide")
ensure_directories()
init_db()

st.markdown(
    """
    <style>
    :root {
        --cp-ink: #111827;
        --cp-muted: #667085;
        --cp-line: #d0d5dd;
        --cp-line-soft: #e4e7ec;
        --cp-panel: #ffffff;
        --cp-soft: #f9fafb;
        --cp-blue: #1f4e79;
        --cp-blue-soft: #eef4ff;
        --cp-green: #067647;
        --cp-green-soft: #ecfdf3;
        --cp-amber: #b54708;
        --cp-amber-soft: #fffaeb;
        --cp-red: #b42318;
        --cp-red-soft: #fef3f2;
    }
    html, body, .stApp, button, input, textarea, [data-baseweb="select"] {
        font-family: "Segoe UI", Inter, Arial, sans-serif;
    }
    header[data-testid="stHeader"] {
        display: none;
        height: 0;
    }
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    .stDeployButton,
    #MainMenu,
    footer {
        display: none;
    }
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 0;
    }
    .stApp {
        background: #f3f4f6;
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1160px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--cp-ink);
    }
    [data-testid="stSidebar"] {
        background: #101828;
        border-right: 1px solid #1d2939;
    }
    [data-testid="stSidebar"] * {
        color: #f2f4f7;
    }
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] p {
        color: #cdd5df;
    }
    [data-testid="stSidebar"] .stMarkdown {
        font-size: 0.92rem;
    }
    div[data-testid="stTabs"] button {
        font-weight: 600;
        color: #475467;
        border-radius: 0;
        padding-bottom: 0.55rem;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--cp-blue);
    }
    .cp-page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        border: 1px solid var(--cp-line);
        border-radius: 4px;
        background: #ffffff;
        padding: 0.95rem 1rem;
        margin-bottom: 0.85rem;
    }
    .cp-page-title {
        font-size: 1.38rem;
        line-height: 1.18;
        font-weight: 720;
        margin: 0;
        color: var(--cp-ink);
    }
    .cp-page-copy {
        margin: 0.28rem 0 0;
        max-width: 780px;
        color: var(--cp-muted);
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .cp-system-line {
        min-width: 270px;
        color: #344054;
        font-size: 0.8rem;
        line-height: 1.55;
        text-align: right;
        white-space: nowrap;
    }
    .cp-system-line span {
        color: var(--cp-muted);
    }
    .cp-section-heading {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--cp-line-soft);
        padding: 0.1rem 0 0.55rem;
        margin: 0.65rem 0 0.9rem;
    }
    .cp-section-title {
        color: var(--cp-ink);
        font-size: 1rem;
        font-weight: 700;
    }
    .cp-section-note {
        color: var(--cp-muted);
        font-size: 0.78rem;
    }
    .cp-sidebar-brand {
        padding: 0.65rem 0 0.95rem;
        border-bottom: 1px solid #344054;
        margin-bottom: 0.8rem;
    }
    .cp-logo {
        width: 36px;
        height: 36px;
        border-radius: 6px;
        background: #1f4e79;
        color: #ffffff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 720;
        margin-right: 0.6rem;
    }
    .cp-sidebar-title {
        display: inline-block;
        vertical-align: top;
        font-size: 1rem;
        line-height: 1.1;
        font-weight: 700;
        margin-top: 0.08rem;
    }
    .cp-sidebar-subtitle {
        display: block;
        color: #cdd5df;
        font-size: 0.78rem;
        font-weight: 500;
        margin-top: 0.18rem;
    }
    .cp-sidebar-section {
        border-bottom: 1px solid #344054;
        padding: 0 0 0.7rem;
        margin-bottom: 0.75rem;
    }
    .cp-sidebar-label {
        color: #98a2b3;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }
    .cp-status-row,
    .cp-count-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        padding: 0.42rem 0;
        color: #e4e7ec;
        font-size: 0.86rem;
    }
    .cp-status-value,
    .cp-count-value {
        color: #ffffff;
        font-weight: 700;
    }
    .cp-status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 0.45rem;
        background: #98a2b3;
    }
    .cp-status-dot.good { background: var(--cp-green); }
    .cp-status-dot.info { background: #2e90fa; }
    .cp-stat-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0;
        margin: 0 0 0.95rem;
        border: 1px solid var(--cp-line);
        border-radius: 4px;
        overflow: hidden;
        background: #ffffff;
    }
    .cp-stat {
        background: #ffffff;
        border-right: 1px solid var(--cp-line-soft);
        border-radius: 0;
        padding: 0.72rem 0.85rem;
        min-height: 74px;
    }
    .cp-stat:last-child { border-right: 0; }
    .cp-stat-label {
        color: var(--cp-muted);
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .cp-stat-value {
        color: var(--cp-ink);
        font-size: 1.28rem;
        font-weight: 720;
        margin-top: 0.14rem;
        line-height: 1.15;
    }
    .cp-stat-note {
        color: var(--cp-muted);
        font-size: 0.74rem;
        margin-top: 0.15rem;
    }
    .cp-panel {
        background: var(--cp-panel);
        border: 1px solid var(--cp-line);
        border-radius: 6px;
        padding: 0.9rem;
        margin-bottom: 0.85rem;
    }
    .cp-panel-title {
        color: var(--cp-ink);
        font-size: 0.96rem;
        font-weight: 700;
        margin: 0 0 0.5rem;
    }
    .cp-muted {
        color: var(--cp-muted);
        font-size: 0.86rem;
    }
    .cp-badge {
        display: inline-block;
        padding: 0.18rem 0.42rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 650;
        border: 1px solid var(--cp-line);
        color: #344054;
        background: #ffffff;
        margin-right: 0.28rem;
        margin-bottom: 0.25rem;
    }
    .cp-badge-blue {background: var(--cp-blue-soft); color: var(--cp-blue); border-color: #b2ccff;}
    .cp-badge-green {background: var(--cp-green-soft); color: var(--cp-green); border-color: #abefc6;}
    .cp-badge-amber {background: var(--cp-amber-soft); color: var(--cp-amber); border-color: #fedf89;}
    .cp-badge-red {background: var(--cp-red-soft); color: var(--cp-red); border-color: #fecdca;}
    .cp-progress-track {
        width: 100%;
        height: 8px;
        background: #eaecf0;
        border-radius: 4px;
        overflow: hidden;
        margin: 0.45rem 0 0.25rem;
    }
    .cp-progress-fill {
        height: 100%;
        border-radius: 4px;
        background: var(--cp-blue);
    }
    .cp-progress-fill.good {background: var(--cp-green);}
    .cp-progress-fill.warn {background: var(--cp-amber);}
    .cp-progress-fill.risk {background: var(--cp-red);}
    .cp-timeline {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.4rem;
        margin: 0.75rem 0 0.35rem;
    }
    .cp-step {
        border: 1px solid var(--cp-line);
        border-radius: 6px;
        background: #ffffff;
        padding: 0.5rem 0.42rem;
        min-height: 54px;
    }
    .cp-step.done {
        background: var(--cp-blue-soft);
        border-color: #b2ccff;
    }
    .cp-step-title {
        color: var(--cp-ink);
        font-size: 0.74rem;
        font-weight: 700;
        line-height: 1.12;
    }
    .cp-step-note {
        color: var(--cp-muted);
        font-size: 0.7rem;
        margin-top: 0.15rem;
    }
    .cp-case-card {
        background: #ffffff;
        border: 1px solid var(--cp-line);
        border-left: 3px solid var(--cp-blue);
        border-radius: 6px;
        padding: 0.75rem 0.85rem;
        margin-bottom: 0.6rem;
    }
    .cp-case-title {
        color: var(--cp-ink);
        font-weight: 700;
        font-size: 0.94rem;
    }
    .cp-case-meta {
        color: var(--cp-muted);
        font-size: 0.8rem;
        margin-top: 0.22rem;
    }
    .cp-divider {
        height: 1px;
        background: var(--cp-line);
        margin: 0.8rem 0;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        border-radius: 4px;
        background: #ffffff;
        border-color: var(--cp-line);
        color: var(--cp-ink);
        font-size: 0.9rem;
    }
    .stTextInput input {
        min-height: 2.45rem;
    }
    .stTextArea textarea {
        min-height: 9.5rem;
    }
    .stButton button, .stDownloadButton button {
        border-radius: 4px;
        font-weight: 650;
        min-height: 2.35rem;
    }
    .stButton button[kind="primary"],
    .stDownloadButton button[kind="primary"] {
        background: var(--cp-blue);
        border-color: var(--cp-blue);
    }
    .stFileUploader {
        border: 1px dashed var(--cp-line);
        border-radius: 4px;
        padding: 0.35rem 0.6rem;
        background: #ffffff;
    }
    @media (max-width: 900px) {
        .cp-stat-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
        .cp-stat:nth-child(2) {border-right: 0;}
        .cp-stat:nth-child(-n+2) {border-bottom: 1px solid var(--cp-line-soft);}
        .cp-timeline {grid-template-columns: repeat(2, minmax(0, 1fr));}
        .cp-page-header {align-items: flex-start; flex-direction: column;}
        .cp-system-line {text-align: left; white-space: normal;}
    }
    @media (max-width: 560px) {
        .cp-stat-grid {grid-template-columns: 1fr;}
        .cp-stat {border-right: 0; border-bottom: 1px solid var(--cp-line-soft);}
        .cp-stat:last-child {border-bottom: 0;}
        .cp-page-title {font-size: 1.28rem;}
        .cp-timeline {grid-template-columns: 1fr;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def persist_upload(uploaded_file) -> tuple[str | None, str | None]:
    if not uploaded_file:
        return None, None
    suffix = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    path = UPLOADS_DIR / filename
    path.write_bytes(uploaded_file.getbuffer())
    return str(path), uploaded_file.name


def safe(value: object) -> str:
    return html_escape("" if value is None else str(value))


def badge_class(value: str | None) -> str:
    normalized = (value or "").lower()
    if normalized in {"high", "escalated", "needs_more_evidence"}:
        return "cp-badge-red"
    if normalized in {"medium", "draft_saved", "draft_pending_approval"}:
        return "cp-badge-amber"
    if normalized in {"approved", "resolved", "low"}:
        return "cp-badge-green"
    return "cp-badge-blue"


def evidence_class(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 55:
        return "warn"
    return "risk"


def render_badge(label: object, variant: str | None = None) -> str:
    text = safe(label)
    css_class = variant or badge_class(text)
    return f"<span class='cp-badge {css_class}'>{text}</span>"


def render_stat_card(label: str, value: object, note: str = "") -> str:
    return (
        "<div class='cp-stat'>"
        f"<div class='cp-stat-label'>{safe(label)}</div>"
        f"<div class='cp-stat-value'>{safe(value)}</div>"
        f"<div class='cp-stat-note'>{safe(note)}</div>"
        "</div>"
    )


def render_stat_grid(cards: list[tuple[str, object, str]]) -> None:
    html = "<div class='cp-stat-grid'>" + "".join(render_stat_card(*card) for card in cards) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_evidence_bar(score: int) -> None:
    bounded = max(0, min(100, int(score or 0)))
    st.markdown(
        (
            "<div class='cp-progress-track'>"
            f"<div class='cp-progress-fill {evidence_class(bounded)}' style='width:{bounded}%;'></div>"
            "</div>"
            f"<div class='cp-muted'>Evidence quality: {bounded}/100</div>"
        ),
        unsafe_allow_html=True,
    )


def render_workflow_timeline(trace: list[str]) -> None:
    groups = [
        ("Receive", "receive_complaint", "Input cleaned"),
        ("Analyze", "image_evidence_analyzer", "Image/text checked"),
        ("Classify", "classify_issue", "Issue selected"),
        ("Score", "check_evidence_quality", "Evidence scored"),
        ("Route", "route_department", "Department set"),
        ("Draft", "generate_complaint_draft", "Ready for approval"),
    ]
    trace_set = set(trace or [])
    steps = []
    for title, node, note in groups:
        done = node in trace_set
        steps.append(
            "<div class='cp-step {done_class}'>"
            f"<div class='cp-step-title'>{safe(title)}</div>"
            f"<div class='cp-step-note'>{safe(note if done else 'Pending')}</div>"
            "</div>".format(done_class="done" if done else "")
        )
    st.markdown("<div class='cp-timeline'>" + "".join(steps) + "</div>", unsafe_allow_html=True)


def case_status_counts(cases: list[dict]) -> dict[str, int]:
    counts = {"approved": 0, "resolved": 0, "escalated": 0, "draft": 0}
    for case in cases:
        status = (case.get("case_status") or "").lower()
        if status == "approved":
            counts["approved"] += 1
        elif status == "resolved":
            counts["resolved"] += 1
        elif status == "escalated":
            counts["escalated"] += 1
        elif "draft" in status:
            counts["draft"] += 1
    return counts


def render_case_card(case: dict) -> None:
    score = int(case.get("evidence_score") or 0)
    title = f"{case.get('issue_category') or 'Unknown issue'}"
    location = case.get("location") or "Location not provided"
    department = case.get("department") or "Department not routed"
    created = case.get("created_at") or ""
    badges = (
        render_badge(case.get("urgency_level") or "Unknown")
        + render_badge(case.get("case_status") or "draft")
        + render_badge(f"{score}/100", "cp-badge-blue")
    )
    st.markdown(
        (
            "<div class='cp-case-card'>"
            f"<div class='cp-case-title'>{safe(title)}</div>"
            f"<div>{badges}</div>"
            f"<div class='cp-case-meta'>{safe(location)} | {safe(department)}</div>"
            f"<div class='cp-case-meta'>{safe(created)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_analysis(state: dict) -> None:
    st.markdown("<div class='cp-panel-title'>Analysis summary</div>", unsafe_allow_html=True)
    render_stat_grid(
        [
            ("Issue", state.get("issue_category", "Unknown"), "Detected category"),
            ("Urgency", state.get("urgency_level", "Low"), "Priority level"),
            ("Evidence", f"{state.get('evidence_score', 0)}/100", "Complaint strength"),
            ("Status", state.get("case_status", "draft"), "Workflow state"),
        ]
    )

    st.markdown(
        (
            "<div class='cp-panel'>"
            f"<div class='cp-panel-title'>Responsible department</div>"
            f"{render_badge(state.get('department', 'Local Government Complaint Cell'), 'cp-badge-blue')}"
            f"{render_badge(state.get('urgency_level', 'Low'))}"
            f"{render_badge(state.get('case_status', 'draft'))}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    render_evidence_bar(int(state.get("evidence_score") or 0))
    render_workflow_timeline(state.get("node_trace") or [])

    if state.get("image_summary"):
        st.caption(state["image_summary"])
    if state.get("vision_issue_category"):
        confidence = float(state.get("vision_confidence") or 0)
        st.markdown(
            render_badge(f"Gemini Vision: {state.get('vision_issue_category')} ({confidence:.0%})", "cp-badge-green"),
            unsafe_allow_html=True,
        )
    if state.get("image_evidence_notes"):
        with st.expander("Image evidence notes"):
            for note in state.get("image_evidence_notes") or []:
                st.write(f"- {note}")

    missing = state.get("missing_details") or []
    if missing:
        st.warning("Missing evidence: " + ", ".join(missing))
        for question in state.get("followup_questions") or []:
            st.write(f"- {question}")
    else:
        st.success("Evidence is strong enough for a clean complaint draft.")

    st.markdown("<div class='cp-divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='cp-panel-title'>Complaint draft</div>", unsafe_allow_html=True)
    edited = st.text_area(
        "Draft",
        value=state.get("complaint_draft", ""),
        height=260,
        label_visibility="collapsed",
        key="draft_editor",
    )
    st.session_state.analysis_state["complaint_draft"] = edited

    action_cols = st.columns([1, 1, 2])
    if action_cols[0].button("Approve and save", type="primary", use_container_width=True):
        approved_state = dict(st.session_state.analysis_state)
        approved_state["complaint_draft"] = edited
        approved_state["user_approved"] = True
        approved_state["needs_human_approval"] = False
        approved_state["case_status"] = "approved"
        approved_state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        case_id = save_case(approved_state)
        st.session_state.saved_case_id = case_id
        st.success(f"Saved case {case_id}.")

    if action_cols[1].button("Save as draft", use_container_width=True):
        draft_state = dict(st.session_state.analysis_state)
        draft_state["complaint_draft"] = edited
        draft_state["case_status"] = "draft_saved"
        draft_state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        case_id = save_case(draft_state)
        st.session_state.saved_case_id = case_id
        st.info(f"Draft saved as case {case_id}.")

    if st.session_state.get("saved_case_id"):
        saved = get_case(st.session_state.saved_case_id)
        if saved:
            pdf_path = generate_case_pdf(saved)
            st.download_button(
                "Download case PDF",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
            )


all_cases = list_cases()
counts = case_status_counts(all_cases)
high_urgency_count = sum(1 for case in all_cases if (case.get("urgency_level") or "").lower() == "high")
avg_score = int(sum(int(case.get("evidence_score") or 0) for case in all_cases) / len(all_cases)) if all_cases else 0
text_ai_status = "Configured" if OptionalLLMClient.from_env().configured else "Local fallback"
vision_status = "Configured" if GeminiVisionClient.from_env().configured else "Local fallback"

st.sidebar.markdown(
    """
    <div class='cp-sidebar-brand'>
        <span class='cp-logo'>CP</span>
        <span class='cp-sidebar-title'>CivicProof AI<span class='cp-sidebar-subtitle'>Civic complaint evidence system</span></span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"""
    <div class='cp-sidebar-section'>
        <div class='cp-sidebar-label'>System</div>
        <div class='cp-status-row'><span><span class='cp-status-dot good'></span>LangGraph</span><span class='cp-status-value'>Active</span></div>
        <div class='cp-status-row'><span><span class='cp-status-dot info'></span>Text AI</span><span class='cp-status-value'>{safe(text_ai_status)}</span></div>
        <div class='cp-status-row'><span><span class='cp-status-dot info'></span>Vision</span><span class='cp-status-value'>{safe(vision_status)}</span></div>
    </div>
    <div class='cp-sidebar-section'>
        <div class='cp-sidebar-label'>Case Load</div>
        <div class='cp-count-row'><span>Total cases</span><span class='cp-count-value'>{len(all_cases)}</span></div>
        <div class='cp-count-row'><span>High urgency</span><span class='cp-count-value'>{high_urgency_count}</span></div>
        <div class='cp-count-row'><span>Resolved</span><span class='cp-count-value'>{counts['resolved']}</span></div>
        <div class='cp-count-row'><span>Escalated</span><span class='cp-count-value'>{counts['escalated']}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class='cp-page-header'>
        <div>
            <div class='cp-page-title'>CivicProof AI Operations Console</div>
            <div class='cp-page-copy'>Structured civic complaint intake, evidence review, department routing, approval, follow-up, and PDF reporting.</div>
        </div>
        <div class='cp-system-line'>
            LangGraph <span>active</span><br/>
            Text AI <span>{safe(text_ai_status)}</span><br/>
            Vision <span>{safe(vision_status)}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_stat_grid(
    [
        ("Total cases", len(all_cases), "Saved complaint records"),
        ("High urgency", high_urgency_count, "Needs faster follow-up"),
        ("Avg evidence", f"{avg_score}/100", "Across saved cases"),
        ("Resolved", counts["resolved"], "Closed case records"),
    ]
)

new_tab, cases_tab, report_tab = st.tabs(["New complaint", "Case dashboard", "Project report"])

with new_tab:
    st.markdown(
        "<div class='cp-section-heading'><div class='cp-section-title'>Complaint intake</div><div class='cp-section-note'>New case analysis</div></div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.25, 0.85], gap="large")
    with left:
        complaint_text = st.text_area(
            "Complaint text",
            placeholder="Example: Sewage water is overflowing near my street and children pass through this road daily.",
            height=170,
        )
        uploaded_file = st.file_uploader("Evidence image", type=["png", "jpg", "jpeg", "webp"])
        if uploaded_file:
            st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

    with right:
        st.markdown("<div class='cp-panel-title'>Case details</div>", unsafe_allow_html=True)
        citizen_name = st.text_input("Citizen name", value="Citizen")
        location = st.text_input("Location")
        landmark = st.text_input("Nearby landmark")
        date_time = st.text_input("Date/time", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        language = st.selectbox("Language", SUPPORTED_LANGUAGES)
        style = st.selectbox("Draft style", SUPPORTED_STYLES)

        analyze_clicked = st.button("Analyze complaint", type="primary", use_container_width=True)

    if analyze_clicked:
        image_path, original_name = persist_upload(uploaded_file)
        with st.spinner("Running LangGraph civic workflow..."):
            state = analyze_complaint(
                user_input=complaint_text,
                image_path=image_path,
                image_filename=original_name,
                citizen_name=citizen_name,
                location=location,
                landmark=landmark,
                date_time=date_time,
                language=language,
                complaint_style=style,
            )
        st.session_state.analysis_state = dict(state)
        st.session_state.saved_case_id = None

    if st.session_state.get("analysis_state"):
        render_analysis(st.session_state.analysis_state)

with cases_tab:
    cases = list_cases()
    if not cases:
        st.info("No saved cases yet.")
    else:
        dashboard_counts = case_status_counts(cases)
        dashboard_high = sum(1 for case in cases if (case.get("urgency_level") or "").lower() == "high")
        render_stat_grid(
            [
                ("Approved", dashboard_counts["approved"], "Ready for follow-up"),
                ("Drafts", dashboard_counts["draft"], "Pending approval"),
                ("Escalated", dashboard_counts["escalated"], "Needs attention"),
                ("High urgency", dashboard_high, "Priority cases"),
            ]
        )

        filter_cols = st.columns([1, 1, 2])
        issue_options = ["All"] + sorted({case.get("issue_category") or "Unknown" for case in cases})
        status_options = ["All"] + sorted({case.get("case_status") or "draft" for case in cases})
        issue_filter = filter_cols[0].selectbox("Issue filter", issue_options)
        status_filter = filter_cols[1].selectbox("Status filter", status_options)
        filtered_cases = [
            case
            for case in cases
            if (issue_filter == "All" or (case.get("issue_category") or "Unknown") == issue_filter)
            and (status_filter == "All" or (case.get("case_status") or "draft") == status_filter)
        ]
        filter_cols[2].markdown(
            f"<div class='cp-panel'><div class='cp-panel-title'>{len(filtered_cases)} matching cases</div>"
            f"<div class='cp-muted'>Current dashboard selection.</div></div>",
            unsafe_allow_html=True,
        )

        if not filtered_cases:
            st.info("No cases match the selected filters.")
        else:
            preview_cols = st.columns(min(3, max(1, len(filtered_cases))))
            for index, case in enumerate(filtered_cases[:3]):
                with preview_cols[index % len(preview_cols)]:
                    render_case_card(case)

            case_labels = [
                f"{case['case_id'][:8]} | {case.get('issue_category')} | {case.get('case_status')} | {case.get('created_at')}"
                for case in filtered_cases
            ]
            selected_label = st.selectbox("Saved cases", case_labels)
            selected_index = case_labels.index(selected_label)
            selected = filtered_cases[selected_index]

            render_stat_grid(
                [
                    ("Issue", selected.get("issue_category", ""), "Selected case"),
                    ("Urgency", selected.get("urgency_level", ""), "Priority level"),
                    ("Evidence", f"{selected.get('evidence_score', 0)}/100", "Complaint strength"),
                    ("Status", selected.get("case_status", ""), "Current state"),
                ]
            )

            st.markdown(
                (
                    "<div class='cp-panel'>"
                    f"<div class='cp-panel-title'>Selected case</div>"
                    f"{render_badge(selected.get('department'), 'cp-badge-blue')}"
                    f"{render_badge(selected.get('location') or 'Location not provided')}"
                    f"{render_badge(selected.get('case_status') or 'draft')}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            render_evidence_bar(int(selected.get("evidence_score") or 0))
            st.text_area("Complaint draft", value=selected.get("complaint_draft") or "", height=220)
            st.text_area("Follow-up", value=selected.get("followup_message") or "", height=100)
            st.text_area("Escalation", value=selected.get("escalation_message") or "", height=100)

            case_action_cols = st.columns([1, 1, 2])
            if case_action_cols[0].button("Mark resolved", use_container_width=True):
                update_case_status(selected["case_id"], "resolved")
                st.success("Case marked resolved.")
                st.rerun()
            if case_action_cols[1].button("Mark escalated", use_container_width=True):
                update_case_status(selected["case_id"], "escalated")
                st.success("Case marked escalated.")
                st.rerun()

            pdf_path = generate_case_pdf(selected)
            st.download_button(
                "Download selected case PDF",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
            )

with report_tab:
    report_path = DOCS_DIR / "CivicProof_AI_Project_Report.pdf"
    st.markdown("<div class='cp-panel-title'>Project report</div>", unsafe_allow_html=True)
    if report_path.exists():
        report_size = report_path.stat().st_size / 1024
        st.markdown(
            (
                "<div class='cp-panel'>"
                "<div class='cp-panel-title'>Complete technical report</div>"
                f"<div class='cp-muted'>Includes the complete LangGraph flow diagram, nodes, edges, state, prompts, tools, evidence model, and testing flow. Size: {report_size:.1f} KB.</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.download_button(
            "Download complete project report PDF",
            data=report_path.read_bytes(),
            file_name=report_path.name,
            mime="application/pdf",
            type="primary",
        )
    else:
        st.info("The project report PDF will appear here after running scripts/generate_project_report.py.")
