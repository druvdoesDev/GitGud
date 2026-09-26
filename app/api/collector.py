"""
Event persistence helpers for TRACR.

Responsibilities:
  - Resolve the path to data/events.jsonl relative to the project root,
    regardless of the current working directory.
  - Append a single EventPayload to the file as a JSON line.
  - Read back the most recent N lines for GET /events.

Design notes:
  - File I/O is intentionally synchronous. For a local hackathon demo with
    one writer at a time this is perfectly adequate.
  - The data directory is created on first write if it doesn't already exist.
  - The file is opened in append mode ('a') so existing events are never
    overwritten or truncated.
  - The BI layer reads the same file; we never lock, rotate, or rename it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.api.schema import EventPayload

# Resolve data/ relative to this file's location:
#   app/api/collector.py  →  ../../data/events.jsonl
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
EVENTS_FILE = _DATA_DIR / "events.jsonl"


def _ensure_data_dir() -> None:
    """Create the data directory if it does not exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_event(event: EventPayload) -> None:
    """
    Serialize *event* to a JSON line and append it to data/events.jsonl.

    The datetime field is serialised as an ISO-8601 string so the BI layer
    can parse it with any standard JSON library.
    """
    _ensure_data_dir()

    # model_dump with mode="json" converts datetime → ISO-8601 string
    record: dict[str, Any] = event.model_dump(mode="json")

    with EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def read_recent_events(limit: int = 100) -> list[dict[str, Any]]:
    """
    Return the most recent *limit* events from data/events.jsonl.

    Returns an empty list if the file does not exist or is empty.
    Silently skips any line that cannot be parsed as JSON (defensive against
    partial writes at the tail of the file).
    """
    if not EVENTS_FILE.exists():
        return []

    lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()

    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip malformed lines without crashing

    # Return the tail — most recent events last in the file
    return events[-limit:]
