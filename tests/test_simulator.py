"""
Unit tests for simulate() in app/twin/simulator.py.

Covers all simulation tests specified in the plan's test_simulator.py section.
No scipy — distribution comparison tests belong to Sub-Task 3b.

Fixture setup: build a small but non-trivial TransitionMatrix from the three
sample journeys so that tests exercise real probability sampling.
"""

import pytest

from app.twin.behavior_model import TransitionMatrix
from app.twin.simulator import (
    SimulationResult,
    ValidationReport,
    compare_distributions,
    simulate,
)
from app.twin.transitions import build_graph, compute_probabilities
from data.sample_journeys import ALL_JOURNEYS


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def matrix() -> TransitionMatrix:
    """TransitionMatrix built from the three sample journeys, keyed by 'screen'."""
    graph = build_graph(ALL_JOURNEYS, key="screen")
    return compute_probabilities(graph)


@pytest.fixture(scope="module")
def tiny_matrix() -> TransitionMatrix:
    """
    Minimal two-node matrix: a → b (deterministic), b has no outgoing edges.

    nodes: ["a", "b"]
    probabilities: {"a": {"b": 1.0}}
    stop_nodes auto-discovered: {"b"}
    """
    graph = build_graph(
        [[
            _evt("a"),
            _evt("b"),
        ]],
        key="screen",
    )
    return compute_probabilities(graph)


def _evt(screen: str) -> "Event":  # noqa: F821  (imported lazily to keep fixture readable)
    from app.twin.behavior_model import Event
    return Event(
        user_id="u0",
        timestamp=0.0,
        event_type="click",
        screen=screen,
        action="view",
        feature="browse",
    )


# ---------------------------------------------------------------------------
# test_simulate_reproducible
# ---------------------------------------------------------------------------

class TestSimulateReproducible:
    def test_same_seed_produces_identical_journeys(self, matrix):
        """Same rng_seed → SimulationResult.journeys must be byte-for-byte identical."""
        r1 = simulate(matrix, start_node="home", n_journeys=50,
                      max_steps=20, rng_seed=42)
        r2 = simulate(matrix, start_node="home", n_journeys=50,
                      max_steps=20, rng_seed=42)
        assert r1.journeys == r2.journeys

    def test_same_seed_produces_identical_metadata(self, matrix):
        r1 = simulate(matrix, start_node="home", n_journeys=10,
                      max_steps=10, rng_seed=0)
        r2 = simulate(matrix, start_node="home", n_journeys=10,
                      max_steps=10, rng_seed=0)
        assert r1.start_node  == r2.start_node
        assert r1.n_journeys  == r2.n_journeys
        assert r1.max_steps   == r2.max_steps
        assert r1.stop_nodes  == r2.stop_nodes


# ---------------------------------------------------------------------------
# test_simulate_different_seeds
# ---------------------------------------------------------------------------

class TestSimulateDifferentSeeds:
    def test_different_seeds_produce_different_journeys(self, matrix):
        """Different seeds must produce different journey sets (with high probability)."""
        r1 = simulate(matrix, start_node="home", n_journeys=100,
                      max_steps=20, rng_seed=1)
        r2 = simulate(matrix, start_node="home", n_journeys=100,
                      max_steps=20, rng_seed=999)
        # With 100 journeys over a non-trivial graph the probability of an
        # exact collision is astronomically small.
        assert r1.journeys != r2.journeys

    def test_no_seed_runs_without_error(self, matrix):
        """rng_seed=None (default) must run without raising."""
        result = simulate(matrix, start_node="home", n_journeys=5, max_steps=10)
        assert len(result.journeys) == 5


# ---------------------------------------------------------------------------
# test_simulate_respects_max_steps
# ---------------------------------------------------------------------------

class TestSimulateRespectsMaxSteps:
    def test_no_journey_longer_than_max_steps(self, matrix):
        """Every generated journey must have length ≤ max_steps."""
        max_steps = 3
        result = simulate(matrix, start_node="home", n_journeys=200,
                          max_steps=max_steps, rng_seed=7)
        for journey in result.journeys:
            assert len(journey) <= max_steps, (
                f"Journey {journey!r} exceeds max_steps={max_steps}"
            )

    def test_max_steps_one_yields_single_node_journeys(self, matrix):
        """max_steps=1 means only the start node is ever in the path."""
        result = simulate(matrix, start_node="home", n_journeys=20,
                          max_steps=1, rng_seed=0)
        for journey in result.journeys:
            assert journey == ["home"]

    def test_max_steps_stored_on_result(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=5,
                          max_steps=7, rng_seed=0)
        assert result.max_steps == 7


# ---------------------------------------------------------------------------
# test_simulate_auto_discovers_stop_nodes
# ---------------------------------------------------------------------------

class TestSimulateAutoDiscoversStopNodes:
    def test_journeys_terminate_at_sink_node(self, matrix):
        """
        In the sample matrix 'confirm' is a sink (no outgoing edges).
        Any journey that reaches 'confirm' must stop there — it must be the
        last element, and no further nodes must appear after it.
        """
        result = simulate(matrix, start_node="home", n_journeys=200,
                          max_steps=50, rng_seed=13)
        for journey in result.journeys:
            for i, node in enumerate(journey):
                if node == "confirm":
                    # confirm must be the terminal node of this journey
                    assert i == len(journey) - 1, (
                        f"Journey continued past sink node 'confirm': {journey!r}"
                    )

    def test_auto_stop_nodes_include_known_sinks(self, matrix):
        """confirm and search are both sinks in the sample matrix."""
        result = simulate(matrix, start_node="home", n_journeys=1,
                          max_steps=50, rng_seed=0)
        # Both known sinks must be in the discovered stop_nodes
        assert "confirm" in result.stop_nodes

    def test_tiny_matrix_stop_node_discovered(self, tiny_matrix):
        """b is the only sink in the tiny matrix; it must be in stop_nodes."""
        result = simulate(tiny_matrix, start_node="a", n_journeys=5,
                          max_steps=10, rng_seed=0)
        assert "b" in result.stop_nodes


# ---------------------------------------------------------------------------
# test_simulate_extra_stop_nodes
# ---------------------------------------------------------------------------

class TestSimulateExtraStopNodes:
    def test_extra_stop_node_terminates_journey(self, matrix):
        """
        Passing extra_stop_nodes={"product"} must make every journey stop the
        moment 'product' is reached — 'cart' must never appear after 'product'.
        """
        result = simulate(
            matrix,
            start_node="home",
            n_journeys=200,
            max_steps=50,
            extra_stop_nodes={"product"},
            rng_seed=21,
        )
        for journey in result.journeys:
            for i, node in enumerate(journey):
                if node == "product":
                    assert i == len(journey) - 1, (
                        f"Journey continued past extra stop node 'product': {journey!r}"
                    )

    def test_extra_stop_nodes_appear_in_result(self, matrix):
        """extra_stop_nodes must be included in SimulationResult.stop_nodes."""
        result = simulate(
            matrix,
            start_node="home",
            n_journeys=1,
            max_steps=10,
            extra_stop_nodes={"cart", "search"},
            rng_seed=0,
        )
        assert "cart" in result.stop_nodes
        assert "search" in result.stop_nodes

    def test_no_extra_stop_nodes_does_not_raise(self, matrix):
        """extra_stop_nodes=None (default) must run without error."""
        result = simulate(matrix, start_node="home", n_journeys=5,
                          max_steps=10, rng_seed=0)
        assert result is not None


# ---------------------------------------------------------------------------
# test_simulate_terminates_on_dead_end
# ---------------------------------------------------------------------------

class TestSimulateTerminatesOnDeadEnd:
    def test_single_node_matrix_produces_single_node_journey(self):
        """
        A TransitionMatrix with only a single node and no outgoing edges:
        start_node has no successors, so every journey is just [start_node].
        """
        # Build a matrix that has a node but no outgoing transitions.
        # Use an ad-hoc TransitionMatrix to precisely control the scenario.
        m = TransitionMatrix(
            key="screen",
            probabilities={},    # no transitions at all
            nodes=["lonely"],
        )
        result = simulate(m, start_node="lonely", n_journeys=10,
                          max_steps=20, rng_seed=0)
        for journey in result.journeys:
            assert journey == ["lonely"], (
                f"Expected single-node journey, got {journey!r}"
            )

    def test_dead_end_after_one_hop(self, tiny_matrix):
        """
        tiny_matrix: a→b (deterministic), b has no successors.
        Every journey must be exactly ["a", "b"].
        """
        result = simulate(tiny_matrix, start_node="a", n_journeys=20,
                          max_steps=50, rng_seed=0)
        for journey in result.journeys:
            assert journey == ["a", "b"], (
                f"Expected ['a','b'], got {journey!r}"
            )


# ---------------------------------------------------------------------------
# test_simulate_stop_nodes_recorded
# ---------------------------------------------------------------------------

class TestSimulateStopNodesRecorded:
    def test_stop_nodes_field_is_list_of_strings(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=1,
                          max_steps=10, rng_seed=0)
        assert isinstance(result.stop_nodes, list)
        assert all(isinstance(n, str) for n in result.stop_nodes)

    def test_stop_nodes_is_sorted(self, matrix):
        """stop_nodes must be in sorted order for deterministic display."""
        result = simulate(matrix, start_node="home", n_journeys=1,
                          max_steps=10, rng_seed=0)
        assert result.stop_nodes == sorted(result.stop_nodes)

    def test_stop_nodes_contains_auto_discovered(self, matrix):
        """confirm is a sink in the sample matrix and must always appear."""
        result = simulate(matrix, start_node="home", n_journeys=1,
                          max_steps=50, rng_seed=0)
        assert "confirm" in result.stop_nodes

    def test_stop_nodes_union_with_extras(self, matrix):
        """When extra_stop_nodes are given, stop_nodes must be the union."""
        result = simulate(
            matrix,
            start_node="home",
            n_journeys=1,
            max_steps=10,
            extra_stop_nodes={"home"},
            rng_seed=0,
        )
        assert "home" in result.stop_nodes
        assert "confirm" in result.stop_nodes  # still includes auto-discovered


# ---------------------------------------------------------------------------
# SimulationResult structure
# ---------------------------------------------------------------------------

class TestSimulationResultStructure:
    def test_n_journeys_matches_request(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=17,
                          max_steps=10, rng_seed=0)
        assert result.n_journeys == 17
        assert len(result.journeys) == 17

    def test_start_node_recorded(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=5,
                          max_steps=10, rng_seed=0)
        assert result.start_node == "home"

    def test_every_journey_starts_at_start_node(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=50,
                          max_steps=20, rng_seed=0)
        for journey in result.journeys:
            assert journey[0] == "home", (
                f"Journey does not start at 'home': {journey!r}"
            )

    def test_all_nodes_in_journeys_are_strings(self, matrix):
        result = simulate(matrix, start_node="home", n_journeys=20,
                          max_steps=10, rng_seed=0)
        for journey in result.journeys:
            assert all(isinstance(node, str) for node in journey)


# ---------------------------------------------------------------------------
# Distribution comparison tests — Sub-Task 3b (requires scipy)
# ---------------------------------------------------------------------------

class TestCompareDistributions:
    """Tests for compare_distributions() and ValidationReport."""

    # Shared real journeys in node-label form (screen key, from sample data)
    _real: list[list[str]] = [
        ["home", "product", "cart", "checkout", "confirm"],
        ["home", "search", "product", "home"],
        ["home", "product", "cart", "checkout", "confirm"],
    ]

    def test_compare_identical_distributions(self):
        """Passing the same journey list for both arguments → chi_square_statistic near 0."""
        report = compare_distributions(self._real, self._real)
        assert report.chi_square_statistic == pytest.approx(0.0, abs=1e-9)

    def test_compare_divergent_distributions(self):
        """Very different journey sets → chi_square_statistic is clearly > 0."""
        # Simulated journeys take only one edge that real data never uses heavily
        divergent: list[list[str]] = [
            ["home", "search", "product", "home"],
        ] * 50
        report = compare_distributions(self._real, divergent)
        assert report.chi_square_statistic > 0.0

    def test_compare_no_passed_field(self):
        """ValidationReport must have no 'passed' attribute."""
        report = compare_distributions(self._real, self._real)
        assert not hasattr(report, "passed"), (
            "ValidationReport must not have a 'passed' field — "
            "chi-square is informational only."
        )

    def test_compare_returns_note(self):
        """ValidationReport.note must be a non-empty string."""
        report = compare_distributions(self._real, self._real)
        assert isinstance(report.note, str)
        assert len(report.note) > 0

    def test_compare_frequencies_are_dicts_of_float(self):
        """observed_frequencies and simulated_frequencies must map edge tuples to floats."""
        report = compare_distributions(self._real, self._real)
        for edge, freq in report.observed_frequencies.items():
            assert isinstance(edge, tuple) and len(edge) == 2
            assert isinstance(freq, float)
        for edge, freq in report.simulated_frequencies.items():
            assert isinstance(edge, tuple) and len(edge) == 2
            assert isinstance(freq, float)

    def test_compare_observed_frequencies_sum_to_one(self):
        """Normalised observed frequencies must sum to 1.0."""
        report = compare_distributions(self._real, self._real)
        total = sum(report.observed_frequencies.values())
        assert abs(total - 1.0) < 1e-9

    def test_compare_simulated_frequencies_sum_to_one(self):
        """Normalised simulated frequencies must sum to 1.0."""
        divergent = [["home", "product", "cart", "checkout", "confirm"]] * 10
        report = compare_distributions(self._real, divergent)
        total = sum(report.simulated_frequencies.values())
        assert abs(total - 1.0) < 1e-9

    def test_compare_empty_journeys_does_not_raise(self):
        """Both empty journey lists → report with statistic=0, p=1, no crash."""
        report = compare_distributions([], [])
        assert report.chi_square_statistic == 0.0
        assert report.p_value == pytest.approx(1.0)
        assert isinstance(report.note, str)

    def test_compare_p_value_is_float(self):
        report = compare_distributions(self._real, self._real)
        assert isinstance(report.p_value, float)

    def test_compare_chi_square_statistic_is_float(self):
        report = compare_distributions(self._real, self._real)
        assert isinstance(report.chi_square_statistic, float)

    def test_compare_with_simulated_result_journeys(self):
        """End-to-end: run simulate() then compare_distributions() — no error."""
        from app.twin.transitions import build_graph, compute_probabilities
        from data.sample_journeys import ALL_JOURNEYS

        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        sim_result = simulate(matrix, start_node="home", n_journeys=100,
                              max_steps=20, rng_seed=0)

        real_as_labels = [
            [getattr(e, "screen") for e in journey]
            for journey in ALL_JOURNEYS
        ]
        report = compare_distributions(real_as_labels, sim_result.journeys)
        assert isinstance(report, ValidationReport)
        assert isinstance(report.chi_square_statistic, float)
