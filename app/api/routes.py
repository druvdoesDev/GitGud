"""
TRACR API route definitions.

Endpoints:
  POST /collect
  GET  /events
  GET  /health
  GET  /graph
  GET  /flows
  GET  /anomalies
  GET  /summary
  GET  /whatif/baseline
  POST /whatif/simulate
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api import bi_bridge, collector, whatif
from app.api.schema import EventPayload, WhatIfRequest


# ---------------------------------------------------------------------------
# IMPORTANT:
# app/main.py imports routes.router.
# This object MUST exist at module level.
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# Demo behavioral anomaly helper
# ---------------------------------------------------------------------------

KNOWN_ROUTE = [
    "home",
    "product",
    "cart",
    "checkout",
    "confirmation",
]


def build_demo_anomalies(bundle):
    """
    Build descriptive behavioral alerts for the dashboard.

    These alerts are derived from observed transition data.
    They do not replace the unfinished BI anomaly_detection module.
    """

    anomalies = [
        {
            "type": anomaly.type,
            "description": anomaly.description,
            "severity": anomaly.severity,
        }
        for anomaly in bundle.anomalies
    ]

    seen = {
        (
            item["type"],
            item["description"],
        )
        for item in anomalies
    }

    for edge in bundle.graph.edges:
        if edge.source not in KNOWN_ROUTE:
            continue

        if edge.target not in KNOWN_ROUTE:
            continue

        source_index = KNOWN_ROUTE.index(edge.source)
        target_index = KNOWN_ROUTE.index(edge.target)

        # A transition moving backwards through the normal funnel
        # is surfaced as a descriptive behavioral alert.
        if target_index < source_index:
            if edge.probability >= 0.35:
                severity = "high"
            elif edge.probability >= 0.10:
                severity = "medium"
            else:
                severity = "low"

            item = {
                "type": "Backtracking behavior",
                "description": (
                    f"Observed navigation from "
                    f"{edge.source} back to "
                    f"{edge.target} "
                    f"({edge.probability * 100:.1f}% "
                    f"transition probability)."
                ),
                "severity": severity,
            }

            key = (
                item["type"],
                item["description"],
            )

            if key not in seen:
                anomalies.append(item)
                seen.add(key)

    return anomalies


# ---------------------------------------------------------------------------
# POST /collect
# ---------------------------------------------------------------------------


@router.post("/collect", status_code=201)
def collect_event(
    event: EventPayload,
) -> JSONResponse:
    """
    Receive and persist one behavioral event.
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
    Return the most recent 100 events.
    """

    events = collector.read_recent_events(
        limit=100
    )

    return JSONResponse(
        content={
            "events": events,
            "count": len(events),
        }
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@router.get("/health")
def health() -> JSONResponse:
    """
    API liveness check.
    """

    return JSONResponse(
        content={
            "status": "ok"
        }
    )


# ---------------------------------------------------------------------------
# GET /graph
# ---------------------------------------------------------------------------


@router.get("/graph")
def get_graph() -> JSONResponse:
    """
    Return behavioral graph nodes and transitions.
    """

    bundle = bi_bridge.get_analysis()

    graph = bundle.graph

    nodes = [
        {
            "id": node.id,
            "visit_count": node.visit_count,
        }
        for node in graph.nodes
    ]

    edges = [
        {
            "from": edge.source,
            "to": edge.target,
            "probability": edge.probability,
            "count": edge.count,
        }
        for edge in graph.edges
    ]

    return JSONResponse(
        content={
            "nodes": nodes,
            "edges": edges,
        }
    )


# ---------------------------------------------------------------------------
# GET /flows
# ---------------------------------------------------------------------------


@router.get("/flows")
def get_flows() -> JSONResponse:
    """
    Return ranked observed user flows.
    """

    bundle = bi_bridge.get_analysis()

    flows = [
        {
            "path": flow.path,
            "count": flow.count,
            "share": flow.share,
        }
        for flow in bundle.flows
    ]

    return JSONResponse(
        content={
            "flows": flows,
        }
    )


# ---------------------------------------------------------------------------
# GET /anomalies
# ---------------------------------------------------------------------------


@router.get("/anomalies")
def get_anomalies() -> JSONResponse:
    """
    Return descriptive behavioral alerts.

    The BI anomaly_detection module is not yet implemented, so this endpoint
    supplements the empty BI result with observed route-backtracking alerts.
    """

    bundle = bi_bridge.get_analysis()

    anomalies = build_demo_anomalies(
        bundle
    )

    return JSONResponse(
        content={
            "anomalies": anomalies,
            "count": len(anomalies),
        }
    )


# ---------------------------------------------------------------------------
# GET /summary
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_summary() -> JSONResponse:
    """
    Return session/event summary statistics.
    """

    bundle = bi_bridge.get_analysis()

    summary = bundle.summary

    return JSONResponse(
        content={
            "total_sessions": summary.total_sessions,
            "total_events": summary.total_events,
            "last_updated": (
                summary.last_updated.isoformat()
                if summary.last_updated
                else None
            ),
        }
    )


# ---------------------------------------------------------------------------
# GET /whatif/baseline
# ---------------------------------------------------------------------------


@router.get("/whatif/baseline")
def get_whatif_baseline() -> JSONResponse:
    """
    Return baseline transition probabilities.
    """

    try:
        probabilities = (
            whatif.get_baseline_probabilities()
        )

        return JSONResponse(
            content={
                "probabilities": probabilities
            }
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# POST /whatif/simulate
# ---------------------------------------------------------------------------


@router.post("/whatif/simulate")
def post_whatif_simulate(
    request: WhatIfRequest,
) -> JSONResponse:
    """
    Run baseline and what-if simulations and return deviations/statistics.
    """

    try:
        result = whatif.run_whatif(
            request
        )

        return JSONResponse(
            content=result.model_dump(
                by_alias=True
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc