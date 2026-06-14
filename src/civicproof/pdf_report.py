from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import REPORTS_DIR, ensure_directories


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text or "")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def generate_case_pdf(case: dict[str, Any], output_dir: str | Path | None = None) -> Path:
    ensure_directories()
    target_dir = Path(output_dir or REPORTS_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    case_id = case.get("case_id", "case")
    path = target_dir / f"civicproof_case_{case_id}.pdf"

    styles = getSampleStyleSheet()
    title = styles["Title"]
    heading = styles["Heading2"]
    body = styles["BodyText"]
    body.leading = 14

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    story: list[Any] = []
    story.append(_paragraph("CivicProof AI Complaint Report", title))
    story.append(Spacer(1, 0.18 * inch))

    rows = [
        ["Case ID", case.get("case_id", "")],
        ["Status", case.get("case_status", "")],
        ["Issue", case.get("issue_category", "")],
        ["Urgency", case.get("urgency_level", "")],
        ["Evidence score", f"{case.get('evidence_score', 0)}/100"],
        ["Department", case.get("department", "")],
        ["Location", case.get("location") or ""],
        ["Landmark", case.get("landmark") or ""],
        ["Date/time", case.get("date_time") or ""],
    ]
    table = Table(rows, colWidths=[1.45 * inch, 4.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.22 * inch))

    sections = [
        ("Original Complaint", case.get("complaint_text") or case.get("user_input") or ""),
        ("Generated Complaint Draft", case.get("complaint_draft") or ""),
        ("Missing Evidence", ", ".join(case.get("missing_details") or []) or "No major missing evidence details."),
        ("Follow-up Message", case.get("followup_message") or ""),
        ("Escalation Message", case.get("escalation_message") or ""),
    ]
    for section_title, section_body in sections:
        story.append(_paragraph(section_title, heading))
        story.append(_paragraph(section_body, body))
        story.append(Spacer(1, 0.14 * inch))

    doc.build(story)
    return path
