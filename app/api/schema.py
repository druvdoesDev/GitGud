"""
Pydantic models that define the TRACR data contracts.

This file is the single source of truth for the shapes of:
  - Events sent from the JS snippet to POST /collect
  - The analysis output written by the Behavioral Intelligence layer
    and read by the API endpoints

Both Person B (API) and the BI developer may import from this file.
Do NOT import from app/twin/ or app/analysis/ in this file.

Coordination note: the AnalysisResult shape (and its nested models)
represents a working draft. Confirm field names with the BI developer
before Sub-Task 3 implementation begins. All models use
model_config = {"extra": "ignore"} so the BI layer can add fields
freely without breaking deserialization here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Inbound: events arriving from the JS instrumentation snippet
# ---------------------------------------------------------------------------


class EventPayload(BaseModel):
    """Shape of a single event POSTed to /collect by tracr.js."""

    model_config = {"extra": "ignore"}

    session_id: str = Field(
        ...,
        description="Client-generated UUID stored in sessionStorage.",
    )
    timestamp: datetime = Field(
        ...,
        description="ISO-8601 timestamp set by the client at the moment of the event.",
    )
    page: str = Field(
        ...,
        description="Logical page name, e.g. 'home', 'product', 'cart', 'checkout', 'confirmation'.",
    )
    event: str = Field(
        ...,
        description="Event type, e.g. 'page_view', 'add_to_cart', 'begin_checkout', 'purchase_complete'.",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional free-form key/value pairs attached to the event.",
    )


# ---------------------------------------------------------------------------
# Outbound: behavioral graph served by GET /graph
# ---------------------------------------------------------------------------


class GraphNode(BaseModel):
    """A page (node) in the behavioral transition graph."""

    model_config = {"extra": "ignore"}

    id: str = Field(..., description="Page name, matches EventPayload.page values.")
    visit_count: int = Field(..., description="Total number of visits to this page.")


class GraphEdge(BaseModel):
    """A directional transition between two pages."""

    model_config = {"extra": "ignore"}

    # 'from' is a Python reserved word; use alias for JSON key
    source: str = Field(..., alias="from", description="Origin page name.")
    target: str = Field(..., alias="to", description="Destination page name.")
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Transition probability from source to target (0.0–1.0).",
    )
    count: int = Field(..., description="Raw number of times this transition occurred.")

    model_config = {"extra": "ignore", "populate_by_name": True}


class BehaviorGraph(BaseModel):
    """Complete behavioral transition graph returned by GET /graph."""

    model_config = {"extra": "ignore"}

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Outbound: top user flows served by GET /flows
# ---------------------------------------------------------------------------


class UserFlow(BaseModel):
    """A ranked user journey through the application."""

    model_config = {"extra": "ignore"}

    path: list[str] = Field(
        ...,
        description="Ordered sequence of page names, e.g. ['home', 'product', 'cart'].",
    )
    count: int = Field(..., description="Number of sessions that followed this path.")
    share: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of total sessions that followed this path (0.0–1.0).",
    )


# ---------------------------------------------------------------------------
# Outbound: anomalies served by GET /anomalies
# ---------------------------------------------------------------------------


class Anomaly(BaseModel):
    """A behavioral anomaly detected by the BI layer."""

    model_config = {"extra": "ignore"}

    type: str = Field(..., description="Short anomaly category label.")
    description: str = Field(..., description="Human-readable explanation.")
    severity: Literal["low", "medium", "high"] = Field(
        ...,
        description="Severity level: low | medium | high.",
    )


# ---------------------------------------------------------------------------
# Outbound: summary statistics served by GET /summary
# ---------------------------------------------------------------------------


class AnalysisSummary(BaseModel):
    """High-level statistics about the collected event data."""

    model_config = {"extra": "ignore"}

    total_sessions: int = Field(default=0)
    total_events: int = Field(default=0)
    last_updated: datetime | None = Field(
        default=None,
        description="When the BI layer last wrote analysis.json.",
    )


# ---------------------------------------------------------------------------
# Full analysis.json shape (written by BI layer, read by API)
# ---------------------------------------------------------------------------


class AnalysisResult(BaseModel):
    """
    Top-level structure of data/analysis.json.

    The BI layer writes this file; Person B's API reads it.
    All nested models tolerate extra fields so BI can extend freely.
    """

    model_config = {"extra": "ignore"}

    graph: BehaviorGraph = Field(default_factory=BehaviorGraph)
    top_flows: list[UserFlow] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)
