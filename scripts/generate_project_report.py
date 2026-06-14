from __future__ import annotations

import sys
from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from civicproof.config import DOCS_DIR, ensure_directories
from civicproof.state import CivicState


BLUE = colors.HexColor("#2563eb")
BLUE_LIGHT = colors.HexColor("#dbeafe")
GREEN = colors.HexColor("#059669")
GREEN_LIGHT = colors.HexColor("#dcfce7")
AMBER = colors.HexColor("#d97706")
AMBER_LIGHT = colors.HexColor("#fef3c7")
SLATE = colors.HexColor("#334155")
SLATE_LIGHT = colors.HexColor("#f1f5f9")
RED = colors.HexColor("#dc2626")
RED_LIGHT = colors.HexColor("#fee2e2")
GRID = colors.HexColor("#cbd5e1")


GRAPH_NODES = [
    "receive_complaint",
    "detect_input_type",
    "image_evidence_analyzer",
    "text_issue_analyzer",
    "classify_issue",
    "check_urgency",
    "check_evidence_quality",
    "ask_followup_questions",
    "route_department",
    "generate_complaint_draft",
    "human_approval",
    "create_followup_plan",
]

GRAPH_EDGES = [
    ("START", "receive_complaint", "normal start"),
    ("receive_complaint", "detect_input_type", "after normalization"),
    ("detect_input_type", "image_evidence_analyzer", "image or mixed input"),
    ("detect_input_type", "text_issue_analyzer", "text-only input"),
    ("image_evidence_analyzer", "text_issue_analyzer", "after image analysis"),
    ("text_issue_analyzer", "classify_issue", "after text/LLM summary"),
    ("classify_issue", "check_urgency", "category selected"),
    ("check_urgency", "check_evidence_quality", "priority selected"),
    ("check_evidence_quality", "ask_followup_questions", "score below 75"),
    ("check_evidence_quality", "route_department", "score 75 or higher"),
    ("ask_followup_questions", "route_department", "still route with warnings"),
    ("route_department", "generate_complaint_draft", "department selected"),
    ("generate_complaint_draft", "human_approval", "draft ready"),
    ("human_approval", "create_followup_plan", "approval state prepared"),
    ("create_followup_plan", "END", "workflow finished"),
]


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def bullet(items: list[str], style: ParagraphStyle) -> list[Paragraph]:
    return [paragraph(f"- {item}", style) for item in items]


def table_paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text or "")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def wrapped_table_rows(
    rows: list[list[object]],
    header_style: ParagraphStyle,
    cell_style: ParagraphStyle,
) -> list[list[Paragraph]]:
    return [
        [table_paragraph(value, header_style if row_index == 0 else cell_style) for value in row]
        for row_index, row in enumerate(rows)
    ]


def table_style(header_color=BLUE_LIGHT) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def add_arrow(drawing: Drawing, x1: float, y1: float, x2: float, y2: float, color=SLATE, label: str | None = None) -> None:
    drawing.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.4))
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) > abs(dy):
        direction = 1 if dx >= 0 else -1
        points = [x2, y2, x2 - 7 * direction, y2 + 4, x2 - 7 * direction, y2 - 4]
    else:
        direction = 1 if dy >= 0 else -1
        points = [x2, y2, x2 - 4, y2 - 7 * direction, x2 + 4, y2 - 7 * direction]
    drawing.add(Polygon(points, fillColor=color, strokeColor=color))
    if label:
        drawing.add(String((x1 + x2) / 2, (y1 + y2) / 2 + 5, label, fontSize=7, fillColor=color, textAnchor="middle"))


def add_box(
    drawing: Drawing,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    fill=SLATE_LIGHT,
    stroke=BLUE,
    font_size: int = 8,
) -> None:
    drawing.add(Rect(x, y, width, height, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1.1))
    lines = []
    max_chars = max(12, int(width / (font_size * 0.52)))
    for part in label.split("\n"):
        lines.extend(wrap(part, width=max_chars) or [""])
    total_height = (len(lines) - 1) * (font_size + 1)
    for index, line in enumerate(lines):
        drawing.add(
            String(
                x + width / 2,
                y + height / 2 + total_height / 2 - index * (font_size + 1) - 3,
                line,
                fontSize=font_size,
                fillColor=colors.HexColor("#172033"),
                textAnchor="middle",
            )
        )


def workflow_diagram() -> Drawing:
    d = Drawing(500, 640)
    w = 175
    h = 36
    cx = (500 - w) / 2
    left = 10
    right = 315
    y = {
        "start": 595,
        "receive": 550,
        "detect": 505,
        "image": 448,
        "text": 448,
        "classify": 390,
        "urgency": 345,
        "evidence": 300,
        "ask": 238,
        "route": 238,
        "draft": 180,
        "approval": 135,
        "follow": 90,
        "end": 45,
    }
    add_box(d, cx, y["start"], w, h, "START", GREEN_LIGHT, GREEN)
    add_box(d, cx, y["receive"], w, h, "receive_complaint")
    add_box(d, cx, y["detect"], w, h, "detect_input_type", AMBER_LIGHT, AMBER)
    add_box(d, left, y["image"], w, h, "image_evidence_analyzer\nGemini Vision + Pillow", BLUE_LIGHT, BLUE)
    add_box(d, right, y["text"], w, h, "text_issue_analyzer\nGroq optional", BLUE_LIGHT, BLUE)
    add_box(d, cx, y["classify"], w, h, "classify_issue")
    add_box(d, cx, y["urgency"], w, h, "check_urgency")
    add_box(d, cx, y["evidence"], w, h, "check_evidence_quality", AMBER_LIGHT, AMBER)
    add_box(d, left, y["ask"], w, h, "ask_followup_questions")
    add_box(d, right, y["route"], w, h, "route_department")
    add_box(d, cx, y["draft"], w, h, "generate_complaint_draft")
    add_box(d, cx, y["approval"], w, h, "human_approval", RED_LIGHT, RED)
    add_box(d, cx, y["follow"], w, h, "create_followup_plan")
    add_box(d, cx, y["end"], w, h, "END", GREEN_LIGHT, GREEN)

    add_arrow(d, cx + w / 2, y["start"], cx + w / 2, y["receive"] + h)
    add_arrow(d, cx + w / 2, y["receive"], cx + w / 2, y["detect"] + h)
    add_arrow(d, cx + 10, y["detect"], left + w / 2, y["image"] + h, AMBER, "image/mixed")
    add_arrow(d, cx + w - 10, y["detect"], right + w / 2, y["text"] + h, AMBER, "text-only")
    add_arrow(d, left + w, y["image"] + h / 2, right, y["text"] + h / 2, BLUE, "image facts")
    add_arrow(d, right + w / 2, y["text"], cx + w / 2, y["classify"] + h)
    add_arrow(d, cx + w / 2, y["classify"], cx + w / 2, y["urgency"] + h)
    add_arrow(d, cx + w / 2, y["urgency"], cx + w / 2, y["evidence"] + h)
    add_arrow(d, cx + 8, y["evidence"], left + w / 2, y["ask"] + h, AMBER, "score < 75")
    add_arrow(d, cx + w - 8, y["evidence"], right + w / 2, y["route"] + h, GREEN, "score >= 75")
    add_arrow(d, left + w, y["ask"] + h / 2, right, y["route"] + h / 2, BLUE, "warnings")
    add_arrow(d, right + w / 2, y["route"], cx + w / 2, y["draft"] + h)
    add_arrow(d, cx + w / 2, y["draft"], cx + w / 2, y["approval"] + h)
    add_arrow(d, cx + w / 2, y["approval"], cx + w / 2, y["follow"] + h)
    add_arrow(d, cx + w / 2, y["follow"], cx + w / 2, y["end"] + h)
    return d


def architecture_diagram() -> Drawing:
    d = Drawing(500, 260)
    add_box(d, 20, 175, 110, 48, "Citizen\nText + Image", GREEN_LIGHT, GREEN, 8)
    add_box(d, 150, 175, 135, 48, "Streamlit UI\nForm, dashboard,\nPDF buttons", BLUE_LIGHT, BLUE, 8)
    add_box(d, 315, 175, 150, 48, "LangGraph Agent\nStateGraph + nodes\n+ conditional edges", AMBER_LIGHT, AMBER, 8)
    add_box(d, 20, 65, 130, 55, "Local Tools\nRules, Pillow,\nevidence scoring", SLATE_LIGHT, SLATE, 8)
    add_box(d, 185, 65, 130, 55, "AI APIs\nGroq text\nGemini Vision", RED_LIGHT, RED, 8)
    add_box(d, 350, 65, 130, 55, "Outputs\nSQLite cases\nReportLab PDFs", GREEN_LIGHT, GREEN, 8)
    add_arrow(d, 130, 199, 150, 199)
    add_arrow(d, 285, 199, 315, 199)
    add_arrow(d, 390, 175, 85, 120, SLATE, "calls")
    add_arrow(d, 390, 175, 250, 120, RED, "optional")
    add_arrow(d, 390, 175, 415, 120, GREEN, "save/export")
    add_arrow(d, 415, 65, 85, 65, SLATE, "case history supports future analysis")
    return d


def prompt_flow_diagram() -> Drawing:
    d = Drawing(500, 310)
    add_box(d, 18, 238, 120, 45, "Input prompt\nComplaint text", BLUE_LIGHT, BLUE, 8)
    add_box(d, 190, 238, 120, 45, "Image upload\nOptional photo", BLUE_LIGHT, BLUE, 8)
    add_box(d, 18, 155, 140, 52, "Text analyzer prompt\nReturn summary,\ncategory, location", AMBER_LIGHT, AMBER, 8)
    add_box(d, 180, 155, 145, 52, "Vision prompt\nReturn JSON:\ncategory, urgency,\nvisible evidence", AMBER_LIGHT, AMBER, 8)
    add_box(d, 350, 155, 130, 52, "Local rules\nkeywords,\nscore, route", SLATE_LIGHT, SLATE, 8)
    add_box(d, 92, 58, 130, 52, "CivicState\nmerged facts,\nnode trace", GREEN_LIGHT, GREEN, 8)
    add_box(d, 280, 58, 150, 52, "Draft prompt/template\nformal complaint,\nfollow-up,\nescalation", GREEN_LIGHT, GREEN, 8)
    add_arrow(d, 78, 238, 88, 207, BLUE)
    add_arrow(d, 250, 238, 250, 207, BLUE)
    add_arrow(d, 88, 155, 155, 110, AMBER)
    add_arrow(d, 250, 155, 155, 110, AMBER)
    add_arrow(d, 415, 155, 155, 110, SLATE)
    add_arrow(d, 222, 84, 280, 84, GREEN)
    return d


def state_diagram() -> Drawing:
    d = Drawing(500, 250)
    columns = [
        ("Input", "user_input\nimage_path\ncitizen_name\nlocation\nlandmark"),
        ("Analysis", "input_type\nimage_summary\nissue_category\nurgency_level"),
        ("Evidence", "evidence_score\nmissing_details\nfollowup_questions\ndepartment"),
        ("Output", "complaint_draft\nhuman_approval\ncase_status\nfollowup_message"),
    ]
    x = 20
    for title, fields in columns:
        add_box(d, x, 150, 105, 60, title, BLUE_LIGHT, BLUE, 9)
        add_box(d, x, 50, 105, 85, fields, SLATE_LIGHT, SLATE, 7)
        x += 122
    add_arrow(d, 125, 180, 142, 180)
    add_arrow(d, 247, 180, 264, 180)
    add_arrow(d, 369, 180, 386, 180)
    drawing_label = "CivicState is the shared memory object passed from node to node."
    d.add(String(250, 20, drawing_label, fontSize=8, fillColor=SLATE, textAnchor="middle"))
    return d


def build_report() -> Path:
    ensure_directories()
    path = DOCS_DIR / "CivicProof_AI_Project_Report.pdf"
    styles = getSampleStyleSheet()
    title = styles["Title"]
    subtitle = styles["Heading2"]
    heading = styles["Heading1"]
    subheading = styles["Heading2"]
    body = styles["BodyText"]
    body.leading = 14
    small = styles["BodyText"]
    small.fontSize = 9
    small.leading = 11
    table_header = ParagraphStyle(
        "TableHeader",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#172033"),
        wordWrap="CJK",
        splitLongWords=1,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=body,
        fontSize=8.2,
        leading=10,
        textColor=colors.HexColor("#172033"),
        wordWrap="CJK",
        splitLongWords=1,
    )

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=46, leftMargin=46, topMargin=46, bottomMargin=46)
    story: list[object] = []

    story.append(paragraph("CivicProof AI", title))
    story.append(paragraph("Smart Civic Complaint and Evidence Agent using LangGraph", subtitle))
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        paragraph(
            "This report explains the complete CivicProof AI project: problem, architecture, LangGraph nodes, state fields, tools, prompts, conditional edges, storage, PDF output, and testing flow.",
            body,
        )
    )
    summary_rows = [
        ["Item", "Project detail"],
        ["Graph nodes", f"{len(GRAPH_NODES)} LangGraph nodes plus START and END"],
        ["Edges", f"{len(GRAPH_EDGES)} directed edges, including 2 conditional routing decisions"],
        ["State fields", f"{len(CivicState.__annotations__)} CivicState fields"],
        ["AI tools", "Groq for text drafting, Gemini Vision for image understanding"],
        ["Local tools", "Pillow image quality check, keyword classifier, evidence scoring, SQLite, ReportLab"],
        ["Frontend", "Streamlit civic complaint dashboard"],
    ]
    summary_table = Table(
        wrapped_table_rows(summary_rows, table_header, table_cell),
        colWidths=[1.35 * inch, doc.width - 1.35 * inch],
    )
    summary_table.setStyle(table_style(GREEN_LIGHT))
    story.append(Spacer(1, 0.16 * inch))
    story.append(summary_table)

    story.append(Spacer(1, 0.22 * inch))
    story.append(paragraph("1. Problem Background", heading))
    story.extend(
        bullet(
            [
                "Citizens see civic problems such as garbage, sewage overflow, road damage, broken streetlights, and water leakage.",
                "A weak complaint often lacks exact location, date/time, nearby landmark, image evidence, and clear department routing.",
                "CivicProof AI strengthens the complaint before submission by converting raw text/images into a structured civic case.",
                "The project is designed for Pakistan-style civic service workflows, but the same structure can be adapted to any city.",
            ],
            body,
        )
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(paragraph("2. What the App Does", heading))
    story.extend(
        bullet(
            [
                "Accepts complaint text, location, landmark, date/time, citizen name, language, and optional image upload.",
                "Uses Gemini Vision, when configured, to analyze image evidence and infer category, urgency, visible evidence, missing details, and confidence.",
                "Uses Groq, when configured, to improve text summaries and complaint drafting.",
                "Uses local rules for fallback classification, urgency, evidence quality scoring, and department routing.",
                "Shows the draft to the user for approval before saving.",
                "Stores cases in SQLite and exports case/project PDFs with ReportLab.",
            ],
            body,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("3. Complete LangGraph Workflow Diagram", heading))
    story.append(workflow_diagram())
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        paragraph(
            "This is the single complete workflow diagram for the PDF. It is implemented in src/civicproof/agent.py using StateGraph. Every node reads and updates the same CivicState object. Conditional edges decide whether the complaint needs image analysis and whether the evidence is strong enough.",
            body,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("4. Node Inventory", heading))
    node_rows = [
        ["#", "Node", "Input read", "Output written", "Role"],
        ["1", "receive_complaint", "raw form data", "case_id, created_at, normalized details", "Creates the initial clean case state."],
        ["2", "detect_input_type", "text/image presence", "input_type", "Routes text, image, or mixed complaints."],
        ["3", "image_evidence_analyzer", "image_path, user_input", "image_summary, vision category, notes", "Uses Pillow and Gemini Vision."],
        ["4", "text_issue_analyzer", "user_input", "extracted_problem, llm_summary", "Summarizes text and extracts hints."],
        ["5", "classify_issue", "text, image summary, vision category", "issue_category", "Chooses civic category."],
        ["6", "check_urgency", "category, complaint text, vision urgency", "urgency_level", "Sets Low, Medium, or High."],
        ["7", "check_evidence_quality", "state details", "evidence_score, missing_details", "Scores complaint strength."],
        ["8", "ask_followup_questions", "missing_details", "followup_questions", "Asks what is needed to strengthen evidence."],
        ["9", "route_department", "issue_category", "department", "Finds responsible department."],
        ["10", "generate_complaint_draft", "state facts, department", "complaint_draft", "Creates formal/WhatsApp/escalation draft."],
        ["11", "human_approval", "draft", "needs_human_approval, status", "Marks draft pending user approval."],
        ["12", "create_followup_plan", "saved facts", "followup_message, escalation_message", "Prepares next-action messages."],
    ]
    node_table = Table(
        wrapped_table_rows(node_rows, table_header, table_cell),
        colWidths=[
            doc.width * 0.055,
            doc.width * 0.22,
            doc.width * 0.20,
            doc.width * 0.225,
            doc.width * 0.30,
        ],
        repeatRows=1,
    )
    node_table.setStyle(table_style(BLUE_LIGHT))
    story.append(node_table)

    story.append(PageBreak())
    story.append(paragraph("5. Edge and Routing Inventory", heading))
    edge_rows = [["#", "From", "To", "Condition / meaning"]]
    for index, (source, target, condition) in enumerate(GRAPH_EDGES, start=1):
        edge_rows.append([str(index), source, target, condition])
    edge_table = Table(
        wrapped_table_rows(edge_rows, table_header, table_cell),
        colWidths=[doc.width * 0.06, doc.width * 0.27, doc.width * 0.27, doc.width * 0.40],
        repeatRows=1,
    )
    edge_table.setStyle(table_style(AMBER_LIGHT))
    story.append(edge_table)
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        paragraph(
            "There are two conditional routers. First, detect_input_type chooses image_evidence_analyzer for image/mixed input or text_issue_analyzer for text-only input. Second, check_evidence_quality chooses ask_followup_questions when evidence_score is below 75, otherwise it routes directly to route_department.",
            body,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("6. System Architecture", heading))
    story.append(Spacer(1, 0.1 * inch))
    story.extend(
        bullet(
            [
                "Streamlit is the user-facing layer for complaint entry, dashboard review, approval, status changes, and downloads.",
                "LangGraph is the orchestration layer. It controls node order, conditional routing, and state updates.",
                "Groq is used for text drafting when the Groq key is configured.",
                "Gemini Vision is used for image understanding when the Gemini key is configured.",
                "SQLite stores approved/draft cases. ReportLab generates case PDFs and this project report.",
            ],
            body,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("7. CivicState Design", heading))
    state_rows = [["Group", "Fields", "Purpose"]]
    state_rows.extend(
        [
            ["Input", "user_input, image_path, image_filename, citizen_name, location, landmark, date_time, language, complaint_style", "Original user complaint information."],
            ["Image", "image_summary, image_evidence_notes, vision_issue_category, vision_urgency_level, vision_confidence", "Local image quality plus Gemini Vision results."],
            ["Analysis", "input_type, extracted_problem, detected_entities, llm_summary, issue_category, urgency_level", "Problem understanding and category decisions."],
            ["Evidence", "evidence_score, missing_details, followup_questions, department", "Complaint strength and routing."],
            ["Output", "complaint_draft, followup_message, escalation_message", "Text the citizen can use after approval."],
            ["Process", "case_id, created_at, needs_human_approval, user_approved, case_status, saved_case_id, node_trace", "Workflow tracking and persistence support."],
        ]
    )
    state_table = Table(
        wrapped_table_rows(state_rows, table_header, table_cell),
        colWidths=[doc.width * 0.15, doc.width * 0.50, doc.width * 0.35],
        repeatRows=1,
    )
    state_table.setStyle(table_style(GREEN_LIGHT))
    story.append(state_table)

    story.append(PageBreak())
    story.append(paragraph("8. Prompt and Tool Flow", heading))
    story.extend(
        bullet(
            [
                "User prompt input: complaint text, such as 'Sewage water is overflowing near Model Town park'.",
                "Gemini Vision prompt input: image bytes plus instruction to return strict JSON with summary, issue_category, urgency_level, visible_evidence, missing_details, and confidence.",
                "Groq text prompt input: complaint facts and request for concise structured analysis or formal complaint drafting.",
                "Local rule input: normalized text and image summary for keyword classification, urgency detection, department mapping, and evidence scoring.",
                "Final draft input: CivicState facts, selected department, language, style, location, evidence score, and citizen name.",
            ],
            body,
        )
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(paragraph("9. Evidence Quality Model", heading))
    evidence_rows = [
        ["Evidence item", "Score effect", "Why it matters"],
        ["Clear description", "+15", "Officer can understand the problem quickly."],
        ["Photo evidence", "+15", "Visual proof makes the case stronger."],
        ["Exact location", "+20", "Field team can find the issue."],
        ["Nearby landmark", "+10", "Helpful in areas without exact addresses."],
        ["Date/time", "+10", "Shows when the issue was observed."],
        ["Recognized category", "+15", "Allows department routing."],
        ["High urgency", "+5", "Raises priority when public risk is likely."],
    ]
    evidence_table = Table(
        wrapped_table_rows(evidence_rows, table_header, table_cell),
        colWidths=[doc.width * 0.28, doc.width * 0.16, doc.width * 0.56],
        repeatRows=1,
    )
    evidence_table.setStyle(table_style(AMBER_LIGHT))
    story.append(evidence_table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(paragraph("Routing rule: evidence_score below 75 goes to ask_followup_questions; score 75 or higher goes directly to route_department.", body))

    story.append(PageBreak())
    story.append(paragraph("10. Tools and APIs", heading))
    tool_rows = [
        ["Tool/API", "Required?", "Where used", "Purpose"],
        ["LangGraph", "Yes", "agent.py", "Graph orchestration, nodes, edges, routing."],
        ["Streamlit", "Yes", "app.py", "User interface and case dashboard."],
        ["SQLite", "Yes", "db.py", "Persistent case history."],
        ["ReportLab", "Yes", "pdf_report.py and report generator", "PDF exports."],
        ["Pillow", "Yes", "image_tools.py", "Local image size/brightness evidence checks."],
        ["Groq API", "Optional", "llm.py", "Better text analysis and complaint drafting."],
        ["Gemini Vision API", "Optional but recommended", "llm.py and image node", "Real image understanding."],
    ]
    tool_table = Table(
        wrapped_table_rows(tool_rows, table_header, table_cell),
        colWidths=[doc.width * 0.22, doc.width * 0.16, doc.width * 0.24, doc.width * 0.38],
        repeatRows=1,
    )
    tool_table.setStyle(table_style(BLUE_LIGHT))
    story.append(tool_table)

    story.append(Spacer(1, 0.18 * inch))
    story.append(paragraph("11. Example Inputs for Testing", heading))
    story.extend(
        bullet(
            [
                "Sewage: 'Sewage water is overflowing near Model Town park and children pass through this road daily.'",
                "Garbage: 'Garbage has been dumped near the school gate for three days and it is causing smell.'",
                "Streetlight: 'Street light is not working near my street and the road becomes very dark at night.'",
                "Road damage: 'There is a large pothole on the main road and bikes are slipping because of it.'",
                "Water leakage: 'A water supply pipe is leaking near the market and clean water is being wasted.'",
                "Image test: upload a civic issue photo with short text. Gemini Vision should show a category/confidence badge in the app.",
            ],
            body,
        )
    )

    story.append(PageBreak())
    story.append(paragraph("12. Current MVP and Future Enhancements", heading))
    story.extend(
        bullet(
            [
                "MVP complete: text/image input, Groq text drafting, Gemini Vision image analysis, LangGraph routing, evidence scoring, approval, SQLite history, follow-up/escalation messages, and PDF export.",
                "Recommended UI enhancement: professional civic dashboard cards, stronger status badges, timeline visualization, and case analytics.",
                "Recommended AI enhancement: duplicate complaint detection using similarity matching over issue, location, and complaint text.",
                "Recommended LangGraph enhancement: checkpoint persistence and true interrupt-based human approval.",
                "Recommended reporting enhancement: monthly PDF reports, department summaries, unresolved case reports, and escalation letters.",
                "Recommended deployment enhancement: Dockerfile, GitHub Actions, screenshots, and Streamlit Cloud/Render deployment guide.",
            ],
            body,
        )
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(paragraph("13. API Key Notes", heading))
    story.append(
        paragraph(
            "The project can run without API keys using local deterministic logic. With keys configured, a strong setup is Groq for text drafting and Gemini Vision for image analysis. API keys must stay in .env and should not be committed to GitHub.",
            body,
        )
    )

    story.append(Spacer(1, 0.18 * inch))
    story.append(paragraph("14. References", heading))
    references = [
        "LangGraph overview, LangChain Docs: https://docs.langchain.com/oss/python/langgraph/overview",
        "LangGraph Graph API, LangChain Docs: https://docs.langchain.com/oss/python/langgraph/graph-api",
        "LangGraph persistence, LangChain Docs: https://docs.langchain.com/oss/python/langgraph/persistence",
        "LangGraph interrupts and human-in-the-loop, LangChain Docs: https://docs.langchain.com/oss/python/langgraph/interrupts",
        "Gemini API docs: https://ai.google.dev/gemini-api/docs",
        "Groq API docs: https://console.groq.com/docs",
        "Pakistan Citizen Portal app listing: https://play.google.com/store/apps/details?id=com.govpk.citizensportal",
        "World Bank, Pakistan Sustainable Solid Waste Management in Mountain Areas: https://documents1.worldbank.org/curated/en/651571618988128529/pdf/Pakistan-Sustainable-Solid-Waste-Management-in-Mountain-Areas.pdf",
    ]
    story.extend(bullet(references, small))

    doc.build(story)
    return path


if __name__ == "__main__":
    output = build_report()
    print(output)
