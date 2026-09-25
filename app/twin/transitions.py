"""
TRACR Behavioral Intelligence — Graph Builder and Transition Probabilities.

Converts a collection of user journeys into a BehavioralGraph (raw counts)
and then into a TransitionMatrix (normalised per-node probability rows).
"""

from __future__ import annotations

from app.twin.behavior_model import BehavioralGraph, Event, GraphKey, TransitionMatrix


def build_graph(journeys: list[list[Event]], key: GraphKey) -> BehavioralGraph:
    """Build a BehavioralGraph from a collection of user journeys.

    Parameters
    ----------
    journeys:
        A list of journeys, each journey being a list of Events sorted
        ascending by timestamp (as returned by ``build_journeys``).
    key:
        The Event field to use as the node label — one of
        ``"screen"``, ``"action"``, or ``"feature"``.

    Returns
    -------
    BehavioralGraph
        Contains transition counts and per-node entry counts.
    """
    graph = BehavioralGraph(key=key)

    for journey in journeys:
        for i in range(len(journey) - 1):
            from_label: str = getattr(journey[i], key)
            to_label: str = getattr(journey[i + 1], key)

            # Transition counts
            if from_label not in graph.transition_counts:
                graph.transition_counts[from_label] = {}
            graph.transition_counts[from_label][to_label] = (
                graph.transition_counts[from_label].get(to_label, 0) + 1
            )

            # Node entry counts: the destination is "entered" on each transition.
            # Also seed the source on the first step of each journey so every
            # node that participates in the graph appears in node_counts.
            graph.node_counts[to_label] = graph.node_counts.get(to_label, 0) + 1

        # Seed the first node of the journey in node_counts (may be a source-only node).
        if journey:
            first_label: str = getattr(journey[0], key)
            if first_label not in graph.node_counts:
                graph.node_counts[first_label] = 0

    return graph


def compute_probabilities(graph: BehavioralGraph) -> TransitionMatrix:
    """Compute a TransitionMatrix from a BehavioralGraph.

    For each source node with outgoing transitions, divides each count by the
    row total to produce ``P(to_node | from_node)``.  Nodes that appear only as
    destinations (no outgoing transitions) are included in ``nodes`` but have no
    row in ``probabilities``, making them discoverable as terminal nodes.

    Parameters
    ----------
    graph:
        A BehavioralGraph produced by ``build_graph``.

    Returns
    -------
    TransitionMatrix
    """
    probabilities: dict[str, dict[str, float]] = {}

    for from_node, targets in graph.transition_counts.items():
        total = sum(targets.values())
        probabilities[from_node] = {
            to_node: count / total for to_node, count in targets.items()
        }

    # Collect all known nodes: sources + all destinations.
    all_nodes: set[str] = set(graph.transition_counts.keys())
    for targets in graph.transition_counts.values():
        all_nodes.update(targets.keys())

    return TransitionMatrix(
        key=graph.key,
        probabilities=probabilities,
        nodes=sorted(all_nodes),
    )
