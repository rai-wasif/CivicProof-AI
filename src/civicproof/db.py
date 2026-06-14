from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import DB_PATH, ensure_directories


SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    citizen_name TEXT,
    complaint_text TEXT,
    image_filename TEXT,
    image_path TEXT,
    location TEXT,
    landmark TEXT,
    date_time TEXT,
    issue_category TEXT,
    urgency_level TEXT,
    evidence_score INTEGER,
    missing_details TEXT,
    followup_questions TEXT,
    department TEXT,
    complaint_draft TEXT,
    followup_message TEXT,
    escalation_message TEXT,
    language TEXT,
    complaint_style TEXT,
    case_status TEXT,
    node_trace TEXT
);
"""


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    ensure_directories()
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    with _connect(db_path) as connection:
        connection.execute(SCHEMA)
        connection.commit()


def save_case(state: dict[str, Any], db_path: str | Path | None = None) -> str:
    init_db(db_path)
    case_id = str(state.get("case_id"))
    now = str(state.get("updated_at") or state.get("approved_at") or state.get("created_at"))
    payload = {
        "case_id": case_id,
        "created_at": state.get("created_at") or now,
        "updated_at": now,
        "citizen_name": state.get("citizen_name"),
        "complaint_text": state.get("user_input"),
        "image_filename": state.get("image_filename"),
        "image_path": state.get("image_path"),
        "location": state.get("location"),
        "landmark": state.get("landmark"),
        "date_time": state.get("date_time"),
        "issue_category": state.get("issue_category"),
        "urgency_level": state.get("urgency_level"),
        "evidence_score": state.get("evidence_score"),
        "missing_details": json.dumps(state.get("missing_details", [])),
        "followup_questions": json.dumps(state.get("followup_questions", [])),
        "department": state.get("department"),
        "complaint_draft": state.get("complaint_draft"),
        "followup_message": state.get("followup_message"),
        "escalation_message": state.get("escalation_message"),
        "language": state.get("language"),
        "complaint_style": state.get("complaint_style"),
        "case_status": state.get("case_status") or "approved",
        "node_trace": json.dumps(state.get("node_trace", [])),
    }
    columns = ", ".join(payload)
    placeholders = ", ".join([f":{key}" for key in payload])
    updates = ", ".join([f"{key}=excluded.{key}" for key in payload if key != "case_id"])

    with _connect(db_path) as connection:
        connection.execute(
            f"INSERT INTO cases ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(case_id) DO UPDATE SET {updates}",
            payload,
        )
        connection.commit()
    return case_id


def list_cases(limit: int = 100, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM cases ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_case(case_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with _connect(db_path) as connection:
        row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_case_status(case_id: str, status: str, db_path: str | Path | None = None) -> None:
    init_db(db_path)
    with _connect(db_path) as connection:
        connection.execute(
            "UPDATE cases SET case_status = ?, updated_at = datetime('now') WHERE case_id = ?",
            (status, case_id),
        )
        connection.commit()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for key in ["missing_details", "followup_questions", "node_trace"]:
        value = data.get(key)
        if isinstance(value, str):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                data[key] = []
    data["user_input"] = data.get("complaint_text")
    return data
