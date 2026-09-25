"""
Unit tests for compute_probabilities() in app/twin/transitions.py.

Covers all tests specified in the plan's test_transitions.py section.
Uses the pre-built fixtures from data/sample_journeys.py and ad-hoc
BehavioralGraph instances for precise edge-case control.
"""

import pytest

from app.twin.behavior_model import BehavioralGraph
from app.twin.transitions import build_graph, compute_probabilities
from data.sample_journeys import ALL_JOURNEYS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph_from_counts(counts: dict[str, dict[str, int]]) -> BehavioralGraph:
    """Build a BehavioralGraph directly from a counts dict (bypasses build_graph)."""
    g = BehavioralGraph(key="screen")
    g.transition_counts = counts
    return g


# ---------------------------------------------------------------------------
# test_probabilities_sum_to_one
# ---------------------------------------------------------------------------

class TestProbabilitiesSumToOne:
    def test_each_row_sums_to_one_sample_journeys(self):
        """Every row in the TransitionMatrix from the sample journeys must sum to 1.0."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)

        for from_node, row in matrix.probabilities.items():
            total = sum(row.values())
            assert abs(total - 1.0) < 1e-9, (
                f"Row for {from_node!r} sums to {total}, expected 1.0"
            )

    def test_each_row_sums_to_one_single_successor(self):
        """A node with a single successor must have probability exactly 1.0."""
        graph = _graph_from_counts({"a": {"b": 5}})
        matrix = compute_probabilities(graph)
        assert abs(sum(matrix.probabilities["a"].values()) - 1.0) < 1e-9

    def test_each_row_sums_to_one_many_successors(self):
        graph = _graph_from_counts({"a": {"b": 1, "c": 2, "d": 7}})
        matrix = compute_probabilities(graph)
        assert abs(sum(matrix.probabilities["a"].values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# test_probabilities_match_counts
# ---------------------------------------------------------------------------

class TestProbabilitiesMatchCounts:
    def test_probabilities_match_plan_values(self):
        """
        Exact probability values derived from the three sample journeys, key='screen'.

        Journey breakdown:
          u1: home→product→cart→checkout→confirm
          u2: home→search→product→home
          u3: home→product→cart→checkout→confirm

        Transition counts from home: product=2, search=1 → total=3
          P(product  | home)     = 2/3
          P(search   | home)     = 1/3
          P(cart     | product)  = 2/3  (product→cart x2, product→home x1 → total=3)
          P(home     | product)  = 1/3
          P(checkout | cart)     = 1.0
          P(confirm  | checkout) = 1.0
          P(product  | search)   = 1.0

        Note: the plan's transition-count table contained a labelling error
        (listed u2 step1 as home→product when it is actually home→search).
        These values are derived from the actual fixture data and verified by
        test_build_graph_counts_transitions.
        """
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        p = matrix.probabilities

        assert abs(p["home"]["product"]     - 2/3) < 1e-9
        assert abs(p["home"]["search"]      - 1/3) < 1e-9
        assert abs(p["product"]["cart"]     - 2/3) < 1e-9
        assert abs(p["product"]["home"]     - 1/3) < 1e-9
        assert abs(p["cart"]["checkout"]    - 1.0) < 1e-9
        assert abs(p["checkout"]["confirm"] - 1.0) < 1e-9
        assert abs(p["search"]["product"]   - 1.0) < 1e-9

    def test_probabilities_match_simple_known_counts(self):
        """Two-successor node with counts 3 and 1 → 0.75 and 0.25."""
        graph = _graph_from_counts({"x": {"y": 3, "z": 1}})
        matrix = compute_probabilities(graph)
        assert abs(matrix.probabilities["x"]["y"] - 0.75) < 1e-9
        assert abs(matrix.probabilities["x"]["z"] - 0.25) < 1e-9


# ---------------------------------------------------------------------------
# test_isolated_node_handled
# ---------------------------------------------------------------------------

class TestIsolatedNodeHandled:
    def test_sink_node_has_no_row_in_probabilities(self):
        """
        A node that only ever appears as a destination (never a source) must
        appear in matrix.nodes but must NOT have a row in matrix.probabilities.
        This is what makes it discoverable as a terminal node by the simulator.
        """
        graph = _graph_from_counts({"a": {"b": 1}})
        matrix = compute_probabilities(graph)

        assert "b" in matrix.nodes
        assert "b" not in matrix.probabilities

    def test_sink_node_does_not_crash(self):
        """compute_probabilities must not raise when sink nodes are present."""
        graph = _graph_from_counts({"start": {"end": 3}})
        matrix = compute_probabilities(graph)   # must not raise
        assert "end" in matrix.nodes

    def test_empty_graph_produces_empty_matrix(self):
        """Empty BehavioralGraph → empty TransitionMatrix with empty nodes list."""
        graph = _graph_from_counts({})
        matrix = compute_probabilities(graph)
        assert matrix.probabilities == {}
        assert matrix.nodes == []

    def test_confirm_is_sink_in_sample_journeys(self):
        """'confirm' never transitions to anything, so it must be absent from probabilities."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        assert "confirm" in matrix.nodes
        assert "confirm" not in matrix.probabilities


# ---------------------------------------------------------------------------
# test_deterministic_node
# ---------------------------------------------------------------------------

class TestDeterministicNode:
    def test_single_successor_probability_is_one(self):
        """A node with exactly one successor must have P=1.0 for that successor."""
        graph = _graph_from_counts({"only_way": {"exit": 42}})
        matrix = compute_probabilities(graph)
        assert matrix.probabilities["only_way"]["exit"] == pytest.approx(1.0)

    def test_cart_to_checkout_is_deterministic(self):
        """In the sample journeys, cart always transitions to checkout."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        assert matrix.probabilities["cart"]["checkout"] == pytest.approx(1.0)
        assert len(matrix.probabilities["cart"]) == 1


# ---------------------------------------------------------------------------
# TransitionMatrix structure
# ---------------------------------------------------------------------------

class TestTransitionMatrixStructure:
    def test_nodes_list_is_sorted(self):
        """matrix.nodes must be a sorted list of all node labels."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        assert matrix.nodes == sorted(matrix.nodes)

    def test_nodes_list_contains_all_nodes(self):
        """matrix.nodes must contain every node that ever appeared as source or destination."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        matrix = compute_probabilities(graph)
        expected = {"home", "product", "cart", "checkout", "confirm", "search"}
        assert expected.issubset(set(matrix.nodes))

    def test_key_is_propagated(self):
        graph = build_graph(ALL_JOURNEYS, key="action")
        matrix = compute_probabilities(graph)
        assert matrix.key == "action"
