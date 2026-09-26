"""
TRACR API route definitions.

Sub-Task 2:
  POST /collect  — accept an event from the JS snippet, persist to events.jsonl
  GET  /events   — return the most recent 100 events
  GET  /health   — liveness check

Sub-Task 3:
  GET /graph     — behavioral transition graph (nodes + edges with probabilities)
  GET /flows     — top user journeys ranked by frequency
  GET /anomalies — detected behavioral anomalies (empty until BI analysis module is implemented)
  GET /summary   — session/event counts and last-updated timestamp
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api import bi_bridge, collector
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


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------


@router.get("/graph")
def get_graph() -> JSONResponse:
    """
    Return the behavioral transition graph derived from collected events.

    Nodes represent pages; edges represent observed transitions with their
    raw counts and conditional probabilities.  Returns an empty graph when
    no events have been collected yet.
    """
    bundle = bi_bridge.get_analysis()
    graph = bundle.graph

    nodes = [{"id": n.id, "visit_count": n.visit_count} for n in graph.nodes]
    edges = [
        {
            "from": e.source,
            "to": e.target,
            "probability": e.probability,
            "count": e.count,
        }
        for e in graph.edges
    ]
    return JSONResponse(content={"nodes": nodes, "edges": edges})


# ---------------------------------------------------------------------------
# GET /flows
# ---------------------------------------------------------------------------


@router.get("/flows")
def get_flows() -> JSONResponse:
    """
    Return the top user journeys ranked by frequency.

    Each flow is an ordered list of page names representing the sequence of
    screens a session visited.  Returns an empty list when no events exist.
    """
    bundle = bi_bridge.get_analysis()
    flows = [
        {"path": f.path, "count": f.count, "share": f.share}
        for f in bundle.flows
    ]
    return JSONResponse(content={"flows": flows})


# ---------------------------------------------------------------------------
# GET /anomalies
# ---------------------------------------------------------------------------


@router.get("/anomalies")
def get_anomalies() -> JSONResponse:
    """
    Return behavioral anomalies detected by the BI analysis layer.

    The app/analysis/anomaly_detection.py module is not yet implemented.
    This endpoint returns an empty list until the BI team populates that module.
    """
    bundle = bi_bridge.get_analysis()
    anomalies = [
        {"type": a.type, "description": a.description, "severity": a.severity}
        for a in bundle.anomalies
    ]
    return JSONResponse(content={"anomalies": anomalies})


# ---------------------------------------------------------------------------
# GET /summary
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_summary() -> JSONResponse:
    """
    Return high-level statistics about the collected behavioral data.

    Includes total session count, total event count, and the timestamp of
    the most recent event.  Returns zero counts when no events exist.
    """
    bundle = bi_bridge.get_analysis()
    s = bundle.summary
    return JSONResponse(
        content={
            "total_sessions": s.total_sessions,
            "total_events": s.total_events,
            "last_updated": s.last_updated.isoformat() if s.last_updated else None,
        }
    )
