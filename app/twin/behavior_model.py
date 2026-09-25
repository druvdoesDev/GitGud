"""
TRACR Behavioral Intelligence — Event Model and Journey Builder.

Canonical data structures and ingestion functions for the behavioral layer.
All other twin/analysis modules depend on the types defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

GraphKey = Literal["screen", "action", "feature"]


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """A single normalised user interaction."""

    user_id: str
    timestamp: float
    event_type: str
    screen: str
    action: str
    feature: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BehavioralGraph:
    """Transition counts extracted from a collection of journeys."""

    key: GraphKey
    # transition_counts[from_node][to_node] = count
    transition_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    # node_counts[node] = total times this node was entered
    node_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class TransitionMatrix:
    """Per-node probability distributions derived from a BehavioralGraph."""

    key: GraphKey
    # probabilities[from_node][to_node] = P(to_node | from_node)
    probabilities: dict[str, dict[str, float]] = field(default_factory=dict)
    # sorted list of all node labels observed in the graph
    nodes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Source field mappings
# ---------------------------------------------------------------------------

# Maps each supported source name to a dict of {source_field: canonical_field}.
# Only fields that differ from the canonical name need an entry.
_SOURCE_MAPS: dict[str, dict[str, str]] = {
    "default": {},  # canonical shape — no remapping needed
    "frontend": {
        "userId": "user_id",
        "ts": "timestamp",
        "type": "event_type",
        "page": "screen",
        # action, feature stay the same
        "meta": "metadata",
    },
    "backend": {
        "uid": "user_id",
        "time": "timestamp",
        "kind": "event_type",
        "route": "screen",
        "op": "action",
        "area": "feature",
        "extra": "metadata",
    },
}

_REQUIRED_FIELDS = ("user_id", "timestamp", "event_type", "screen", "action", "feature")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def normalise(raw: dict, source: str = "default") -> Event:
    """Normalise a raw event dict from a supported source into a canonical Event.

    Parameters
    ----------
    raw:
        Raw event dict from a frontend beacon, backend log, or test fixture.
    source:
        One of ``"default"``, ``"frontend"``, or ``"backend"``.
        Defaults to ``"default"`` (canonical field names, no remapping).

    Returns
    -------
    Event

    Raises
    ------
    ValueError
        If ``source`` is not recognised, or if any required field is missing
        or empty after remapping.
    """
    if source not in _SOURCE_MAPS:
        raise ValueError(
            f"Unknown source {source!r}. Must be one of: {sorted(_SOURCE_MAPS)}"
        )

    mapping = _SOURCE_MAPS[source]
    # Apply remapping: rename keys that appear in the mapping table.
    remapped: dict = {}
    for key, value in raw.items():
        canonical_key = mapping.get(key, key)
        remapped[canonical_key] = value

    # Validate required fields.
    for req in _REQUIRED_FIELDS:
        if req not in remapped or remapped[req] is None or remapped[req] == "":
            raise ValueError(f"Missing or empty required field: {req!r}")

    return Event(
        user_id=str(remapped["user_id"]),
        timestamp=float(remapped["timestamp"]),
        event_type=str(remapped["event_type"]),
        screen=str(remapped["screen"]),
        action=str(remapped["action"]),
        feature=str(remapped["feature"]),
        metadata=dict(remapped.get("metadata") or {}),
    )


def build_journeys(events: list[Event]) -> dict[str, list[Event]]:
    """Group a flat list of Events into per-user journeys sorted by timestamp.

    Parameters
    ----------
    events:
        Flat list of normalised Events (may be from multiple users).

    Returns
    -------
    dict mapping user_id → list[Event] sorted ascending by timestamp.
    """
    journeys: dict[str, list[Event]] = {}
    for event in events:
        journeys.setdefault(event.user_id, []).append(event)
    for user_events in journeys.values():
        user_events.sort(key=lambda e: e.timestamp)
    return journeys
