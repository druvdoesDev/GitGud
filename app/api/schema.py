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
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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
    action: Optional[str] = Field(
        default=None,
        description=(
            "BI layer action label. Defaults to the 'event' value when absent. "
            "Older events stored without this field will use 'event' as the fallback."
        ),
    )
    feature: Optional[str] = Field(
        default=None,
        description=(
            "BI layer feature label. Defaults to the 'page' value when absent. "
            "Older events stored without this field will use 'page' as the fallback."
        ),
    )

    @model_validator(mode="after")
    def _fill_action_feature_defaults(self) -> "EventPayload":
        """Populate action/feature from event/page when not explicitly supplied."""
        if self.action is None:
            self.action = self.event
        if self.feature is None:
            self.feature = self.page
        return self


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


# ---------------------------------------------------------------------------
# What-If: inbound request models
# ---------------------------------------------------------------------------


class WhatIfModification(BaseModel):
    """A single edge-probability override for a what-if scenario."""

    model_config = {"extra": "forbid"}

    from_node: str = Field(
        ...,
        alias="from",
        description="Source page name for this transition.",
    )
    to_node: str = Field(
        ...,
        alias="to",
        description="Destination page name for this transition.",
    )
    probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Desired probability for this transition in the what-if model. "
            "Remaining outgoing probabilities from the same source node will be "
            "re-normalised proportionally."
        ),
    )

    model_config = {"extra": "forbid", "populate_by_name": True}


class WhatIfRequest(BaseModel):
    """Request body for POST /whatif/simulate."""

    model_config = {"extra": "ignore"}

    modifications: list[WhatIfModification] = Field(
        ...,
        min_length=1,
        description="One or more edge-probability overrides to apply to the baseline model.",
    )
    start_node: str | None = Field(
        default=None,
        description=(
            "Node to begin simulated journeys from. "
            "Defaults to the node with the highest visit count when omitted."
        ),
    )
    n_journeys: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Number of synthetic journeys to simulate for each model (baseline and what-if).",
    )
    rng_seed: int = Field(
        default=42,
        description=(
            "Random seed for both simulations. Fixed seed ensures the demo is reproducible: "
            "same request body → same result."
        ),
    )


# ---------------------------------------------------------------------------
# What-If: outbound response models
# ---------------------------------------------------------------------------


class EdgeDeviation(BaseModel):
    """Measured deviation for one directed edge between the baseline and what-if models."""

    model_config = {"extra": "ignore"}

    from_node: str = Field(..., alias="from", description="Source page name.")
    to_node: str = Field(..., alias="to", description="Destination page name.")
    baseline_probability: float = Field(
        ..., description="P(to|from) in the observed baseline TransitionMatrix."
    )
    whatif_probability: float = Field(
        ..., description="P(to|from) in the modified what-if TransitionMatrix."
    )
    absolute_delta: float = Field(
        ...,
        description="whatif_probability − baseline_probability (negative = decrease).",
    )
    relative_delta: float = Field(
        ...,
        description=(
            "absolute_delta / baseline_probability. "
            "0.0 when baseline_probability is 0."
        ),
    )
    simulated_frequency_baseline: float = Field(
        ...,
        description="Fraction of simulated baseline journeys that contained this edge.",
    )
    simulated_frequency_whatif: float = Field(
        ...,
        description="Fraction of simulated what-if journeys that contained this edge.",
    )
    magnitude: float = Field(
        ...,
        ge=0.0,
        description="abs(absolute_delta) — primary ordering and bubble-sizing signal.",
    )
    severity: Literal["low", "medium", "high"] = Field(
        ...,
        description="low: magnitude < 0.10; medium: 0.10–0.30; high: > 0.30.",
    )

    model_config = {"extra": "ignore", "populate_by_name": True}


class JourneyStats(BaseModel):
    """Summary statistics derived from a set of simulated journeys."""

    model_config = {"extra": "ignore"}

    completion_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of journeys that reached the terminal node.",
    )
    mean_length: float = Field(
        ..., description="Mean number of nodes per simulated journey."
    )


class DistributionComparison(BaseModel):
    """Informational chi-square comparison between baseline and what-if simulations."""

    model_config = {"extra": "ignore"}

    chi_square_statistic: float
    p_value: float
    note: str = Field(
        ...,
        description="Plain-English interpretation; always labelled as informational only.",
    )


class WhatIfResult(BaseModel):
    """Response body for POST /whatif/simulate."""

    model_config = {"extra": "ignore"}

    baseline_probabilities: dict[str, dict[str, float]] = Field(
        ...,
        description="Per-edge probabilities from the observed baseline TransitionMatrix.",
    )
    whatif_probabilities: dict[str, dict[str, float]] = Field(
        ...,
        description="Per-edge probabilities from the modified what-if TransitionMatrix.",
    )
    deviations: list[EdgeDeviation] = Field(
        default_factory=list,
        description=(
            "Edges where the probability changed, sorted by magnitude descending. "
            "Only edges with magnitude > 0 are included."
        ),
    )
    distribution_comparison: DistributionComparison | None = Field(
        default=None,
        description="Chi-square comparison between simulated baseline and what-if journeys.",
    )
    journey_stats_baseline: JourneyStats | None = Field(
        default=None,
        description="Completion rate and mean length for simulated baseline journeys.",
    )
    journey_stats_whatif: JourneyStats | None = Field(
        default=None,
        description="Completion rate and mean length for simulated what-if journeys.",
    )
    completion_delta: float | None = Field(
        default=None,
        description=(
            "journey_stats_whatif.completion_rate − journey_stats_baseline.completion_rate. "
            "Negative means what-if model completes fewer journeys."
        ),
    )
