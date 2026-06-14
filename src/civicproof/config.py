from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("CIVICPROOF_DATA_DIR") or BASE_DIR / "data")
UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_DIR = Path(os.getenv("CIVICPROOF_REPORTS_DIR") or BASE_DIR / "reports")
DOCS_DIR = BASE_DIR / "docs"
DB_PATH = DATA_DIR / "civicproof.db"


def ensure_directories() -> None:
    """Create runtime directories used by the app."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
