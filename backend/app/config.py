"""Central configuration. Everything tunable lives here (or in env vars)."""
from __future__ import annotations

import os
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", ROOT / "frontend" / "dist"))

LONDON = ZoneInfo("Europe/London")

# The day-ahead buying team decides on day D-1 for delivery on day D.
# We assume the decision is taken at this London-local time on D-1; forecasts
# published after it cannot be used. Override with the DECISION_CUTOFF env var.
DEFAULT_CUTOFF = os.getenv("DECISION_CUTOFF", "09:00")

# Scope of the exercise: purchase decisions made in January 2026.
DECISION_START = date(2026, 1, 1)
DECISION_END = date(2026, 1, 31)
DEFAULT_DECISION_DATE = date.fromisoformat(os.getenv("DEFAULT_DECISION_DATE", "2026-01-15"))


def parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))
