"""
TRACR BI Bridge — translates raw events into behavioral analysis results.

This module is the sole integration point between Person B's API layer and the
Behavioral Intelligence (BI) layer owned by the other developer.

Responsibilities:
  1. Load all raw event dicts from data/events.jsonl (via collector).
  2. Translate each raw dict into a BI Event dataclass (direct construction —
     we do NOT call normalise() because our EventPayload shape differs from
     all existing source maps in _SOURCE_MAPS).
  3. Call the BI pipeline:  build_journeys → build_graph → compute_probabilities
  4. Shape the BI output types into the Pydantic response models from schema.py.
  5. Cache the result for 5 seconds so rapid dashboard refreshes don't
     reprocess the full file on every call.

Isolation rules:
  - This file MAY import from app.twin (read-only, calling public functions).
  - This file MUST NOT import from app.analysis (all empty; reserved for BI dev).
  - app.twin and app.analysis MUST NOT import from app.api (one-way dependency).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.api import collector
from app.api.schema import (
    AnalysisSummary,
    Anomaly,
    BehaviorGraph,
    GraphEdge,
    GraphNode,
    UserFlow,
)
from app.twin.behavior_model import Event, build_journeys
from app.twin.transitions import build_graph, compute_probabilities

# ---------------------------------------------------------------------------
# Internal result container
# ---------------------------------------------------------------------------

@dataclass
class _AnalysisBundle:
    """All analysis outputs needed by the four API endpoints."""

    graph: BehaviorGraph
    flows: list[UserFlow]
    anomalies: list[Anomaly]
    summary: AnalysisSummary


# ---------------------------------------------------------------------------
# Event translation
# ---------------------------------------------------------------------------

def _raw_to_bi_event(raw: dict[str, Any]) -> Event | None:
    """
    Translate a raw event dict (as stored in events.jsonl) into a BI Event.

    We construct the Event dataclass directly rather than going through
    normalise() because our EventPayload field names differ from every
    existing source map in behavior_model._SOURCE_MAPS.

    Field mapping:
        EventPayload.session_id  → Event.user_id
        EventPayload.timestamp   → Event.timestamp  (ISO-8601 str → Unix float)
        EventPayload.event       → Event.event_type
        EventPayload.page        → Event.screen
        EventPayload.action      → Event.action  (defaults to EventPayload.event)
        EventPayload.feature     → Event.feature (defaults to EventPayload.page)
        EventPayload.properties  → Event.metadata

    Returns None for any record that is missing a required field so one bad
    line never aborts the entire pipeline.
    """
    try:
        session_id: str = raw["session_id"]
        page: str = raw["page"]
        event_type: str = raw["event"]

        # timestamp may be an ISO-8601 string (how we store it) or a float
        ts_raw = raw["timestamp"]
        if isinstance(ts_raw, (int, float)):
            ts_float = float(ts_raw)
        else:
            # Parse ISO-8601 → datetime → Unix timestamp
            dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            ts_float = dt.timestamp()

        return Event(
            user_id=session_id,
            timestamp=ts_float,
            event_type=event_type,
            screen=page,
            action=raw.get("action") or event_type,
            feature=raw.get("feature") or page,
            metadata=dict(raw.get("properties") or {}),
        )
    except (KeyError, ValueError, TypeError):
        return None  # skip malformed records


# ---------------------------------------------------------------------------
# Result shaping helpers
# ---------------------------------------------------------------------------

def _build_behavior_graph(bi_graph, bi_matrix) -> BehaviorGraph:
    """Convert a BehavioralGraph + TransitionMatrix pair into our Pydantic model."""
    nodes = [
        GraphNode(id=node_id, visit_count=count)
        for node_id, count in bi_graph.node_counts.items()
    ]

    edges = []
    for from_node, targets in bi_graph.transition_counts.items():
        row_probs = bi_matrix.probabilities.get(from_node, {})
        for to_node, count in targets.items():
            probability = row_probs.get(to_node, 0.0)
            edges.append(
                GraphEdge.model_validate(
                    {"from": from_node, "to": to_node, "probability": probability, "count": count}
                )
            )

    return BehaviorGraph(nodes=nodes, edges=edges)


def _build_flows(journeys: dict[str, list[Event]], total_sessions: int) -> list[UserFlow]:
    """
    Derive top user flows from the per-session journeys dict.

    A flow is the ordered sequence of screen values for one session.
    Flows are counted across sessions and ranked by frequency descending.
    """
    if total_sessions == 0:
        return []

    path_counts: dict[tuple[str, ...], int] = {}
    for session_events in journeys.values():
        path = tuple(e.screen for e in session_events)
        path_counts[path] = path_counts.get(path, 0) + 1

    flows = [
        UserFlow(
            path=list(path),
            count=count,
            share=round(count / total_sessions, 4),
        )
        for path, count in sorted(path_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return flows


def _build_summary(raw_events: list[dict], journeys: dict) -> AnalysisSummary:
    """Build summary statistics from the raw event list and journeys dict."""
    last_updated: datetime | None = None
    # Use the latest timestamp found in the events themselves
    for raw in raw_events:
        ts_raw = raw.get("timestamp")
        if ts_raw:
            try:
                dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                if last_updated is None or dt > last_updated:
                    last_updated = dt
            except (ValueError, TypeError):
                pass

    return AnalysisSummary(
        total_sessions=len(journeys),
        total_events=len(raw_events),
        last_updated=last_updated,
    )


# ---------------------------------------------------------------------------
# Core analysis pipeline
# ---------------------------------------------------------------------------

def _run_analysis() -> _AnalysisBundle:
    """
    Run the full BI analysis pipeline against the current events.jsonl contents.

    Returns an _AnalysisBundle with all data needed by the four endpoints.
    Returns a fully-empty bundle when there are no events.
    """
    raw_events = collector.read_all_events()

    if not raw_events:
        return _AnalysisBundle(
            graph=BehaviorGraph(),
            flows=[],
            anomalies=[],
            summary=AnalysisSummary(),
        )

    # Translate raw dicts → BI Event objects, dropping any that fail translation
    bi_events: list[Event] = [
        e for raw in raw_events if (e := _raw_to_bi_event(raw)) is not None
    ]

    if not bi_events:
        return _AnalysisBundle(
            graph=BehaviorGraph(),
            flows=[],
            anomalies=[],
            summary=AnalysisSummary(total_events=len(raw_events)),
        )

    # BI pipeline
    journeys = build_journeys(bi_events)
    journey_lists = list(journeys.values())
    bi_graph = build_graph(journey_lists, key="screen")
    bi_matrix = compute_probabilities(bi_graph)

    # Shape into API response models
    graph = _build_behavior_graph(bi_graph, bi_matrix)
    flows = _build_flows(journeys, total_sessions=len(journeys))
    summary = _build_summary(raw_events, journeys)

    # app/analysis/anomaly_detection.py is not yet implemented by the BI team.
    # Return an empty list until that module is available.
    anomalies: list[Anomaly] = []

    return _AnalysisBundle(
        graph=graph,
        flows=flows,
        anomalies=anomalies,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------

_cache_result: _AnalysisBundle | None = None
_cache_ts: float = 0.0
_CACHE_TTL: float = 5.0  # seconds — matches the dashboard auto-refresh interval


def get_analysis() -> _AnalysisBundle:
    """
    Return a cached _AnalysisBundle, recomputing if the cache is older than
    _CACHE_TTL seconds.

    The cache is module-level and in-process only — it is reset every time
    the server restarts.  For a local hackathon demo this is perfectly adequate.
    """
    global _cache_result, _cache_ts
    now = time.monotonic()
    if _cache_result is None or (now - _cache_ts) >= _CACHE_TTL:
        _cache_result = _run_analysis()
        _cache_ts = now
    return _cache_result


def invalidate_cache() -> None:
    """Force the next get_analysis() call to recompute. Used in tests."""
    global _cache_result, _cache_ts
    _cache_result = None
    _cache_ts = 0.0
