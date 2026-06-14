from pathlib import Path

from civicproof.db import get_case, init_db, save_case
from civicproof.pdf_report import generate_case_pdf


def test_save_case_and_generate_pdf(tmp_path: Path):
    db_path = tmp_path / "cases.db"
    init_db(db_path)
    state = {
        "case_id": "case-1",
        "created_at": "2026-06-12T10:00:00",
        "updated_at": "2026-06-12T10:01:00",
        "citizen_name": "Citizen",
        "user_input": "Garbage is dumped near the school gate.",
        "location": "Main Street",
        "landmark": "School gate",
        "date_time": "2026-06-12 10:00",
        "issue_category": "Garbage",
        "urgency_level": "Medium",
        "evidence_score": 85,
        "missing_details": [],
        "followup_questions": [],
        "department": "Solid Waste Management / Municipal Committee",
        "complaint_draft": "Please remove the garbage.",
        "followup_message": "Please share status.",
        "escalation_message": "Please escalate.",
        "language": "English",
        "complaint_style": "Formal government",
        "case_status": "approved",
        "node_trace": ["receive_complaint"],
    }
    save_case(state, db_path)
    saved = get_case("case-1", db_path)
    assert saved is not None
    assert saved["issue_category"] == "Garbage"

    pdf_path = generate_case_pdf(saved, tmp_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
