from civicproof.agent import analyze_complaint
from civicproof.analysis import classify_issue, route_department, score_evidence


def test_classify_issue_detects_sewage():
    category = classify_issue("Sewage water is overflowing near the main street.")
    assert category == "Sewage"


def test_route_department_for_streetlight():
    assert "Lighting" in route_department("Streetlight")


def test_score_evidence_lists_missing_location():
    score, missing = score_evidence(
        {
            "user_input": "Garbage has been dumped for three days.",
            "issue_category": "Garbage",
            "urgency_level": "Medium",
            "date_time": "2026-06-12 10:00",
        }
    )
    assert score < 75
    assert "Exact street, area, or GPS location" in missing


def test_langgraph_agent_generates_draft():
    state = analyze_complaint(
        user_input="Street light is not working near Model Town park and the street is dark.",
        location="Model Town",
        landmark="Park gate",
        citizen_name="Wasif",
    )
    assert state["issue_category"] == "Streetlight"
    assert state["department"]
    assert "Streetlight" in state["complaint_draft"] or "streetlight" in state["complaint_draft"].lower()
    assert "human_approval" in state["node_trace"]


def test_image_only_flow_falls_back_without_vision(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    image_path = tmp_path / "issue.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\x9a\xa9\xf8\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    state = analyze_complaint(user_input="", image_path=str(image_path))
    assert state["input_type"] == "image"
    assert state["image_summary"]
    assert "image_evidence_analyzer" in state["node_trace"]
