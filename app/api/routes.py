"""
TRACR API route definitions.

Sub-Task 2 implements:
  POST /collect  — accept an event from the JS snippet, persist to events.jsonl
  GET  /events   — return the most recent 100 events
  GET  /health   — liveness check

Sub-Task 3 will add:
  GET /graph, GET /flows, GET /anomalies, GET /summary
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api import collector
from app.api.schema import EventPayload

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /collect
# ---------------------------------------------------------------------------


@router.post("/collect", status_code=201)
def collect_event(event: EventPayload) -> JSONResponse:
    """
    Receive a single behavioral event from the tracr.js snippet and persist
    it to data/events.jsonl.

    The request body must match the EventPayload schema.
    FastAPI/Pydantic handles validation and returns 422 on malformed input.
    """
    collector.append_event(event)
    return JSONResponse(
        status_code=201,
        content={
            "status": "ok",
            "session_id": event.session_id,
            "event": event.event,
            "page": event.page,
        },
    )


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------


@router.get("/events")
def get_events() -> JSONResponse:
    """
    Return the most recent 100 events from data/events.jsonl.

    Returns an empty list when no events have been collected yet.
    Events are returned in chronological order (oldest first).
    """
    events = collector.read_recent_events(limit=100)
    return JSONResponse(content={"events": events, "count": len(events)})


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@router.get("/health")
def health() -> JSONResponse:
    """Liveness check. Returns 200 when the API is running."""
    return JSONResponse(content={"status": "ok"})
