"""
Unit tests for build_graph() in app/twin/transitions.py.

Covers all tests specified in the plan's test_graph_builder.py section.
Uses the pre-built Event fixtures from data/sample_journeys.py where possible,
and constructs minimal ad-hoc journeys for edge-case tests.
"""

import pytest

from app.twin.behavior_model import Event
from app.twin.transitions import build_graph
from data.sample_journeys import ALL_JOURNEYS, EVENTS_U1, EVENTS_U2, EVENTS_U3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(screen: str, action: str = "view", feature: str = "browse",
         user_id: str = "u1", ts: float = 1000.0) -> Event:
    return Event(
        user_id=user_id,
        timestamp=ts,
        event_type="click",
        screen=screen,
        action=action,
        feature=feature,
    )


# ---------------------------------------------------------------------------
# test_build_graph_counts_transitions
#
# Uses the three sample journeys keyed by "screen" and verifies the exact
# transition counts from the plan's "Expected Behavioral Graph" section.
# ---------------------------------------------------------------------------

class TestBuildGraphCountsTransitions:
    def test_build_graph_counts_transitions(self):
        """Known journeys → expected count dict.

        Journey breakdown (key='screen'):
          u1: home→product→cart→checkout→confirm
          u2: home→search→product→home
          u3: home→product→cart→checkout→confirm  (repeat of u1)

        Correct counts:
          home→product : 2  (u1, u3)
          home→search  : 1  (u2)
          product→cart : 2  (u1, u3)
          product→home : 1  (u2 returns)
          cart→checkout: 2  (u1, u3)
          checkout→confirm: 2 (u1, u3)
          search→product: 1 (u2)
        """
        graph = build_graph(ALL_JOURNEYS, key="screen")
        tc = graph.transition_counts

        # home outgoing
        assert tc["home"]["product"] == 2
        assert tc["home"]["search"] == 1
        # product outgoing
        assert tc["product"]["cart"] == 2
        assert tc["product"]["home"] == 1
        # deterministic arcs
        assert tc["cart"]["checkout"] == 2
        assert tc["checkout"]["confirm"] == 2
        assert tc["search"]["product"] == 1

    def test_build_graph_no_unexpected_transitions(self):
        """No extra edges should appear beyond those in the plan."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        tc = graph.transition_counts

        assert set(tc["home"].keys()) == {"product", "search"}
        assert set(tc["product"].keys()) == {"cart", "home"}
        assert set(tc["cart"].keys()) == {"checkout"}
        assert set(tc["checkout"].keys()) == {"confirm"}
        assert set(tc["search"].keys()) == {"product"}
        # "confirm" has no outgoing transitions
        assert "confirm" not in tc


# ---------------------------------------------------------------------------
# test_build_graph_configurable_key
# ---------------------------------------------------------------------------

class TestBuildGraphConfigurableKey:
    def test_configurable_key_screen_vs_action(self):
        """key='action' and key='screen' produce different graphs from the same journeys."""
        graph_screen = build_graph(ALL_JOURNEYS, key="screen")
        graph_action = build_graph(ALL_JOURNEYS, key="action")

        # Screen graph starts at "home"; action graph starts at "view"
        assert "home" in graph_screen.transition_counts
        assert "home" not in graph_action.transition_counts

        assert "view" in graph_action.transition_counts
        assert "view" not in graph_screen.transition_counts

    def test_configurable_key_feature(self):
        """key='feature' produces a coarser graph collapsing multiple screens."""
        graph = build_graph(ALL_JOURNEYS, key="feature")
        tc = graph.transition_counts

        # browse → checkout (home→cart via product in journeys 1 & 3)
        assert "browse" in tc
        assert "checkout" in tc["browse"]

    def test_key_is_stored_on_graph(self):
        graph = build_graph(ALL_JOURNEYS, key="action")
        assert graph.key == "action"


# ---------------------------------------------------------------------------
# test_build_graph_single_event_journey
# ---------------------------------------------------------------------------

class TestBuildGraphSingleEventJourney:
    def test_no_transitions_for_single_event_journey(self):
        """A journey with one event contributes zero transitions."""
        single = [_evt("home")]
        graph = build_graph([single], key="screen")
        assert graph.transition_counts == {}

    def test_single_event_still_seeds_node_counts(self):
        """The sole event's node should appear in node_counts even with no transitions."""
        single = [_evt("home")]
        graph = build_graph([single], key="screen")
        assert "home" in graph.node_counts


# ---------------------------------------------------------------------------
# test_build_graph_empty_input
# ---------------------------------------------------------------------------

class TestBuildGraphEmptyInput:
    def test_empty_journey_list(self):
        """Empty input → empty graph with no transitions and no node counts."""
        graph = build_graph([], key="screen")
        assert graph.transition_counts == {}
        assert graph.node_counts == {}

    def test_journey_of_empty_list(self):
        """A journey that is itself empty contributes nothing."""
        graph = build_graph([[]], key="screen")
        assert graph.transition_counts == {}
        assert graph.node_counts == {}


# ---------------------------------------------------------------------------
# test_node_counts_correct
# ---------------------------------------------------------------------------

class TestNodeCountsCorrect:
    def test_node_counts_match_plan(self):
        """
        node_counts[node] = number of times the node was entered (arrived at).
        Starting nodes that are never arrived at from another node have count 0
        (they are seeded by the first-event logic in build_graph).

        Correct expected from the three sample journeys keyed by 'screen':
          u1: home→product→cart→checkout→confirm
          u2: home→search→product→home
          u3: home→product→cart→checkout→confirm

          home:     arrived 1 time  (product→home x1, u2 returns)
          product:  arrived 3 times (home→product x2, search→product x1)
          cart:     arrived 2 times (product→cart x2)
          checkout: arrived 2 times (cart→checkout x2)
          confirm:  arrived 2 times (checkout→confirm x2)
          search:   arrived 1 time  (home→search x1)
        """
        graph = build_graph(ALL_JOURNEYS, key="screen")
        nc = graph.node_counts

        assert nc.get("product",  0) == 3   # home→product x2, search→product x1
        assert nc.get("cart",     0) == 2   # product→cart x2
        assert nc.get("checkout", 0) == 2   # cart→checkout x2
        assert nc.get("confirm",  0) == 2   # checkout→confirm x2
        assert nc.get("search",   0) == 1   # home→search x1
        assert nc.get("home",     0) == 1   # product→home x1 (u2 returns)

    def test_node_counts_all_nodes_present(self):
        """Every node that appears anywhere in the journeys must be in node_counts."""
        graph = build_graph(ALL_JOURNEYS, key="screen")
        expected_nodes = {"home", "product", "cart", "checkout", "confirm", "search"}
        assert expected_nodes.issubset(graph.node_counts.keys())

    def test_first_node_seeded(self):
        """The first node of a journey that never appears as a destination is seeded at 0."""
        journey = [
            _evt("start"),
            _evt("end"),
        ]
        graph = build_graph([journey], key="screen")
        # "start" is only ever a source, never a destination
        assert "start" in graph.node_counts
        assert graph.node_counts["start"] == 0
        # "end" was arrived at once
        assert graph.node_counts["end"] == 1
