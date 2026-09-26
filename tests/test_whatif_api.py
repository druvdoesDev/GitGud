"""
Contract tests for the What-If API endpoints.

  GET  /whatif/baseline  — returns baseline TransitionMatrix probabilities
  POST /whatif/simulate  — returns WhatIfResult for given modifications

Tests verify:
  - HTTP response shapes and status codes
  - Correct behaviour with no events (empty state)
  - Correct behaviour with seeded sample data
  - Re-normalisation of modified rows
  - Completion delta sign and magnitude sanity
  - 422 validation on malformed request bodies
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.api.collector as collector_mod
import app.api.bi_bridge as bi_bridge_mod
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Two sessions that produce a TransitionMatrix with at least one branching node:
#   Session s1: home → product → cart → checkout → confirm
#   Session s2: home → search → product → cart → checkout → confirm
#
# Resulting transitions (keyed by screen):
#   home → product   P=0.5   home → search   P=0.5
#   search → product P=1.0
#   product → cart   P=1.0
#   cart → checkout  P=1.0
#   checkout→confirm P=1.0

_SAMPLE_EVENTS = [
    # Session s1
    {"session_id": "s1", "timestamp": "2024-01-01T10:00:00+00:00", "page": "home",     "event": "page_view", "properties": {}},
    {"session_id": "s1", "timestamp": "2024-01-01T10:00:01+00:00", "page": "product",  "event": "page_view", "properties": {}},
    {"session_id": "s1", "timestamp": "2024-01-01T10:00:02+00:00", "page": "cart",     "event": "page_view", "properties": {}},
    {"session_id": "s1", "timestamp": "2024-01-01T10:00:03+00:00", "page": "checkout", "event": "page_view", "properties": {}},
    {"session_id": "s1", "timestamp": "2024-01-01T10:00:04+00:00", "page": "confirm",  "event": "page_view", "properties": {}},
    # Session s2
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:00+00:00", "page": "home",     "event": "page_view", "properties": {}},
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:01+00:00", "page": "search",   "event": "page_view", "properties": {}},
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:02+00:00", "page": "product",  "event": "page_view", "properties": {}},
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:03+00:00", "page": "cart",     "event": "page_view", "properties": {}},
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:04+00:00", "page": "checkout", "event": "page_view", "properties": {}},
    {"session_id": "s2", "timestamp": "2024-01-01T11:00:05+00:00", "page": "confirm",  "event": "page_view", "properties": {}},
]


@pytest.fixture()
def seeded_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Write _SAMPLE_EVENTS to a temp events.jsonl, patch collector paths,
    and invalidate the bi_bridge cache so tests see the fresh data.
    """
    events_file = tmp_path / "events.jsonl"
    data_dir = tmp_path

    with events_file.open("w") as fh:
        for ev in _SAMPLE_EVENTS:
            fh.write(json.dumps(ev) + "\n")

    monkeypatch.setattr(collector_mod, "EVENTS_FILE", events_file)
    monkeypatch.setattr(collector_mod, "_DATA_DIR", data_dir)
    bi_bridge_mod.invalidate_cache()
    yield events_file
    bi_bridge_mod.invalidate_cache()


@pytest.fixture()
def empty_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Patch collector to a directory with no events.jsonl."""
    monkeypatch.setattr(collector_mod, "EVENTS_FILE", tmp_path / "events.jsonl")
    monkeypatch.setattr(collector_mod, "_DATA_DIR", tmp_path)
    bi_bridge_mod.invalidate_cache()
    yield
    bi_bridge_mod.invalidate_cache()


# ---------------------------------------------------------------------------
# GET /whatif/baseline — no events
# ---------------------------------------------------------------------------


def test_baseline_empty_events(empty_events):
    """Baseline returns 200 with an empty probabilities dict when no data exists."""
    resp = client.get("/whatif/baseline")
    assert resp.status_code == 200
    body = resp.json()
    assert "probabilities" in body
    assert body["probabilities"] == {}


# ---------------------------------------------------------------------------
# GET /whatif/baseline — with events
# ---------------------------------------------------------------------------


def test_baseline_returns_probabilities(seeded_events):
    """Baseline probabilities reflect the edges in the seeded events."""
    resp = client.get("/whatif/baseline")
    assert resp.status_code == 200
    probs = resp.json()["probabilities"]

    # home has two outgoing edges: product (P=0.5) and search (P=0.5)
    assert "home" in probs
    assert abs(probs["home"]["product"] - 0.5) < 1e-6
    assert abs(probs["home"]["search"] - 0.5) < 1e-6

    assert "product" in probs
    assert abs(probs["product"]["cart"] - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# POST /whatif/simulate — validation errors
# ---------------------------------------------------------------------------


def test_simulate_empty_modifications_rejected(seeded_events):
    """Empty modifications list should return 422."""
    resp = client.post(
        "/whatif/simulate",
        json={"modifications": []},
    )
    assert resp.status_code == 422


def test_simulate_bad_probability_rejected(seeded_events):
    """Probability outside [0, 1] should return 422."""
    resp = client.post(
        "/whatif/simulate",
        json={"modifications": [{"from": "home", "to": "product", "probability": 1.5}]},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /whatif/simulate — successful simulation
# ---------------------------------------------------------------------------


def test_simulate_returns_required_fields(seeded_events):
    """Simulate response must contain all top-level WhatIfResult fields."""
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [{"from": "home", "to": "product", "probability": 0.8}],
            "n_journeys": 100,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "baseline_probabilities",
        "whatif_probabilities",
        "deviations",
        "distribution_comparison",
        "journey_stats_baseline",
        "journey_stats_whatif",
        "completion_delta",
    ):
        assert key in body, f"Missing key: {key}"


def test_simulate_deviation_fields(seeded_events):
    """Each deviation entry must have all EdgeDeviation fields with correct types."""
    # Override one of home's two outgoing edges (home→product baseline P=0.5 → 0.8)
    # This will change home→search as well via re-normalisation, producing deviations.
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [{"from": "home", "to": "product", "probability": 0.8}],
            "n_journeys": 50,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    deviations = resp.json()["deviations"]
    assert len(deviations) > 0

    dev = deviations[0]
    for field in (
        "from",
        "to",
        "baseline_probability",
        "whatif_probability",
        "absolute_delta",
        "relative_delta",
        "simulated_frequency_baseline",
        "simulated_frequency_whatif",
        "magnitude",
        "severity",
    ):
        assert field in dev, f"Missing deviation field: {field}"

    # magnitude ≥ 0 and severity is one of the three valid values
    assert dev["magnitude"] >= 0
    assert dev["severity"] in ("low", "medium", "high")


def test_simulate_deviations_sorted_by_magnitude_desc(seeded_events):
    """Deviations must be sorted by magnitude descending."""
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [
                {"from": "home", "to": "product", "probability": 0.8},
            ],
            "n_journeys": 100,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    mags = [d["magnitude"] for d in resp.json()["deviations"]]
    assert mags == sorted(mags, reverse=True)


def test_simulate_row_renormalisation(seeded_events):
    """
    When one edge in a row is overridden, the whatif probabilities for
    all outgoing edges from that source must still sum to 1.0.
    """
    # home has two outgoing edges (product + search). Override home→product to 0.7;
    # home→search should be re-normalised to 0.3 so the row sums to 1.0.
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [{"from": "home", "to": "product", "probability": 0.7}],
            "n_journeys": 50,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    wi_probs = resp.json()["whatif_probabilities"]
    for from_node, targets in wi_probs.items():
        row_sum = sum(targets.values())
        if row_sum > 0:
            assert abs(row_sum - 1.0) < 1e-4, (
                f"Row {from_node!r} does not sum to 1.0: {row_sum}"
            )


def test_simulate_reproducible_with_same_seed(seeded_events):
    """Same request body + seed must return identical deviations."""
    payload = {
        "modifications": [{"from": "home", "to": "product", "probability": 0.8}],
        "n_journeys": 200,
        "rng_seed": 42,
    }
    r1 = client.post("/whatif/simulate", json=payload).json()
    r2 = client.post("/whatif/simulate", json=payload).json()
    assert r1["deviations"] == r2["deviations"]
    assert r1["completion_delta"] == r2["completion_delta"]


def test_simulate_completion_delta_type(seeded_events):
    """completion_delta must be a float (possibly 0.0)."""
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [{"from": "home", "to": "product", "probability": 0.8}],
            "n_journeys": 100,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    delta = resp.json()["completion_delta"]
    assert isinstance(delta, (int, float))


def test_simulate_distribution_comparison_present(seeded_events):
    """distribution_comparison must be present and have the three expected keys."""
    resp = client.post(
        "/whatif/simulate",
        json={
            "modifications": [{"from": "home", "to": "product", "probability": 0.4}],
            "n_journeys": 100,
            "rng_seed": 42,
        },
    )
    assert resp.status_code == 200
    dc = resp.json()["distribution_comparison"]
    assert dc is not None
    assert "chi_square_statistic" in dc
    assert "p_value" in dc
    assert "note" in dc
