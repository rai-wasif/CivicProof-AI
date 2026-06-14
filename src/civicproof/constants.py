from __future__ import annotations

ISSUE_KEYWORDS: dict[str, list[str]] = {
    "Garbage": [
        "garbage",
        "trash",
        "waste",
        "dump",
        "dumping",
        "kachra",
        "filth",
        "solid waste",
        "overflowing bin",
    ],
    "Sewage": [
        "sewage",
        "gutter",
        "drain",
        "blocked drain",
        "dirty water",
        "overflow",
        "naali",
        "sewer",
        "smell",
    ],
    "Road damage": [
        "road",
        "pothole",
        "broken road",
        "crack",
        "khadda",
        "damage",
        "street damaged",
        "manhole",
    ],
    "Streetlight": [
        "street light",
        "streetlight",
        "light",
        "lamp",
        "dark street",
        "bulb",
        "kharab light",
    ],
    "Water leakage": [
        "water leak",
        "leakage",
        "pipe",
        "burst pipe",
        "water supply",
        "pani",
        "standing water",
    ],
}

ISSUE_DEPARTMENTS: dict[str, str] = {
    "Garbage": "Solid Waste Management / Municipal Committee",
    "Sewage": "WASA / Municipal Services / Local Government",
    "Road damage": "Public Works Department / Local Government",
    "Streetlight": "Municipal Lighting Department / Electricity Wing",
    "Water leakage": "Water Supply Department / WASA",
    "Unknown": "Local Government Complaint Cell",
}

URGENCY_KEYWORDS: dict[str, list[str]] = {
    "High": [
        "danger",
        "accident",
        "injury",
        "open manhole",
        "electric",
        "sewage overflow",
        "school",
        "hospital",
        "children",
        "mosquito",
        "disease",
        "main road",
    ],
    "Medium": [
        "smell",
        "traffic",
        "blocked",
        "leakage",
        "dark",
        "standing water",
        "residents",
        "daily",
    ],
}

ISSUE_BASE_URGENCY: dict[str, str] = {
    "Garbage": "Medium",
    "Sewage": "High",
    "Road damage": "Medium",
    "Streetlight": "Medium",
    "Water leakage": "Medium",
    "Unknown": "Low",
}

SUPPORTED_LANGUAGES = ["English", "Roman Urdu", "Urdu script"]
SUPPORTED_STYLES = ["Formal government", "Short WhatsApp", "Escalation"]
