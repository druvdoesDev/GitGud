"""
TRACR What-If Engine.

Provides two public functions consumed by the /whatif routes:

  get_baseline_probabilities()
      → dict[str, dict[str, float]]
      Returns the TransitionMatrix probabilities derived from the current
      observed events, suitable for pre-populating the WhatIfPanel sliders.

  run_whatif(request: WhatIfRequest) → WhatIfResult
      Applies the caller's edge-probability overrides to a deep copy of the
      baseline TransitionMatrix, runs two identical simulations (baseline and
      what-if), computes per-edge deviations, and returns a WhatIfResult.

Design notes:
  - The observed events.jsonl is NEVER modified.
  - All simulation uses app.twin.simulator.simulate() — no second engine.
  - Both simulations share the same rng_seed for reproducibility.
  - Re-normalisation: when a single outgoing probability is overridden the
    remaining outgoing edges from the same source node are scaled so the row
    still sums to 1.0.  If multiple edges from the same source are overridden
    the overrides are applied first, then the remainder is re-normalised.
"""

from __future__ import annotations

import copy
from typing import Any

from app.api import bi_bridge
from app.api.schema import (
    DistributionComparison,
    EdgeDeviation,
    JourneyStats,
    WhatIfModification,
    WhatIfRequest,
    WhatIfResult,
)
from app.twin.behavior_model import TransitionMatrix
from app.twin.simulator import compare_distributions, simulate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _best_start_node(matrix: TransitionMatrix) -> str:
    """Return the node with the highest visit count, falling back to any node."""
    bundle = bi_bridge.get_analysis()
    if bundle.graph.nodes:
        best = max(bundle.graph.nodes, key=lambda n: n.visit_count)
        return best.id
    # Fallback: first node in matrix
    return matrix.nodes[0] if matrix.nodes else "home"


def _apply_modifications(
    matrix: TransitionMatrix,
    modifications: list[WhatIfModification],
) -> TransitionMatrix:
    """
    Return a deep copy of *matrix* with the requested edge-probability overrides
    applied and each affected source row re-normalised to sum to 1.0.

    Re-normalisation strategy:
      1. For each source node that appears in modifications, collect all
         overridden (to_node, probability) pairs.
      2. Clamp the sum of overrides to ≤ 1.0.
      3. Distribute the remaining probability mass proportionally across the
         non-overridden edges in that row.
      4. If the row has only overridden edges, they are normalised among
         themselves and any residual is discarded.
    """
    new_matrix = copy.deepcopy(matrix)

    # Group modifications by source node
    by_source: dict[str, dict[str, float]] = {}
    for mod in modifications:
        by_source.setdefault(mod.from_node, {})[mod.to_node] = mod.probability

    for from_node, overrides in by_source.items():
        row = new_matrix.probabilities.get(from_node)
        if row is None:
            # Source node has no outgoing edges — ignore this modification
            continue

        # Apply overrides
        for to_node, prob in overrides.items():
            if to_node in row:
                row[to_node] = prob
            # If to_node is not in the row we still allow it (new edge)
            else:
                row[to_node] = prob

        # Re-normalise the row
        override_keys = set(overrides.keys())
        override_total = sum(row[k] for k in override_keys if k in row)

        # Cap override total at 1.0 to avoid negative remainders
        if override_total > 1.0:
            scale = 1.0 / override_total
            for k in override_keys:
                if k in row:
                    row[k] *= scale
            override_total = 1.0

        remaining_mass = 1.0 - override_total
        non_override_edges = {k: v for k, v in row.items() if k not in override_keys}
        non_override_total = sum(non_override_edges.values())

        if non_override_total > 0 and remaining_mass > 0:
            scale = remaining_mass / non_override_total
            for k in non_override_edges:
                row[k] *= scale
        elif non_override_total > 0:
            # Override total = 1.0 — zero out all non-overridden edges
            for k in non_override_edges:
                row[k] = 0.0
        else:
            # No non-overridden edges at all — re-normalise overrides themselves
            # so the row sums to 1.0 (e.g. single-edge row overridden to 0.7)
            override_sum = sum(row[k] for k in override_keys if k in row)
            if override_sum > 0:
                for k in override_keys:
                    if k in row:
                        row[k] /= override_sum

        new_matrix.probabilities[from_node] = row

    return new_matrix


def _count_edge_in_journeys(
    journeys: list[list[str]], from_node: str, to_node: str
) -> float:
    """Return the fraction of journeys that contain the edge (from_node → to_node)."""
    if not journeys:
        return 0.0
    total = sum(
        1
        for j in journeys
        for i in range(len(j) - 1)
        if j[i] == from_node and j[i + 1] == to_node
    )
    return total / len(journeys)


def _journey_stats(journeys: list[list[str]], stop_nodes: list[str]) -> JourneyStats:
    """Compute completion rate and mean journey length."""
    if not journeys:
        return JourneyStats(completion_rate=0.0, mean_length=0.0)
    stop_set = set(stop_nodes)
    completed = sum(1 for j in journeys if j and j[-1] in stop_set)
    mean_len = sum(len(j) for j in journeys) / len(journeys)
    return JourneyStats(
        completion_rate=round(completed / len(journeys), 4),
        mean_length=round(mean_len, 4),
    )


def _classify_severity(magnitude: float) -> str:
    if magnitude > 0.30:
        return "high"
    if magnitude >= 0.10:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_baseline_probabilities() -> dict[str, dict[str, float]]:
    """Return TransitionMatrix probabilities from the current observed events."""
    bundle = bi_bridge.get_analysis()
    # Rebuild the matrix from the graph edges stored in the bundle
    probs: dict[str, dict[str, float]] = {}
    for edge in bundle.graph.edges:
        probs.setdefault(edge.source, {})[edge.target] = edge.probability
    return probs


def run_whatif(request: WhatIfRequest) -> WhatIfResult:
    """
    Apply modifications to a deep-copied baseline matrix, simulate both
    scenarios, and return a WhatIfResult with deviations + stats.
    """
    bundle = bi_bridge.get_analysis()

    # Reconstruct a TransitionMatrix from the stored graph
    probs: dict[str, dict[str, float]] = {}
    for edge in bundle.graph.edges:
        probs.setdefault(edge.source, {})[edge.target] = edge.probability

    nodes = [n.id for n in bundle.graph.nodes]
    baseline_matrix = TransitionMatrix(key="screen", probabilities=probs, nodes=nodes)

    # Determine start node
    start_node = request.start_node or _best_start_node(baseline_matrix)

    # Simulate baseline
    baseline_result = simulate(
        matrix=baseline_matrix,
        start_node=start_node,
        n_journeys=request.n_journeys,
        max_steps=20,
        rng_seed=request.rng_seed,
    )

    # Apply modifications and simulate what-if
    whatif_matrix = _apply_modifications(baseline_matrix, request.modifications)
    whatif_result = simulate(
        matrix=whatif_matrix,
        start_node=start_node,
        n_journeys=request.n_journeys,
        max_steps=20,
        rng_seed=request.rng_seed,
    )

    # Compute deviations across all edges in the union of both matrices
    baseline_probs = baseline_matrix.probabilities
    whatif_probs = whatif_matrix.probabilities

    all_from_nodes = set(baseline_probs) | set(whatif_probs)
    deviations: list[EdgeDeviation] = []

    for from_node in all_from_nodes:
        b_row = baseline_probs.get(from_node, {})
        w_row = whatif_probs.get(from_node, {})
        all_to_nodes = set(b_row) | set(w_row)
        for to_node in all_to_nodes:
            b_prob = b_row.get(to_node, 0.0)
            w_prob = w_row.get(to_node, 0.0)
            delta = w_prob - b_prob
            magnitude = abs(delta)
            if magnitude == 0.0:
                continue
            rel_delta = delta / b_prob if b_prob > 0 else 0.0
            sim_freq_b = _count_edge_in_journeys(baseline_result.journeys, from_node, to_node)
            sim_freq_w = _count_edge_in_journeys(whatif_result.journeys, from_node, to_node)
            deviations.append(
                EdgeDeviation.model_validate(
                    {
                        "from": from_node,
                        "to": to_node,
                        "baseline_probability": round(b_prob, 6),
                        "whatif_probability": round(w_prob, 6),
                        "absolute_delta": round(delta, 6),
                        "relative_delta": round(rel_delta, 6),
                        "simulated_frequency_baseline": round(sim_freq_b, 6),
                        "simulated_frequency_whatif": round(sim_freq_w, 6),
                        "magnitude": round(magnitude, 6),
                        "severity": _classify_severity(magnitude),
                    }
                )
            )

    deviations.sort(key=lambda d: d.magnitude, reverse=True)

    # Distribution comparison (informational)
    vr = compare_distributions(baseline_result.journeys, whatif_result.journeys)
    dist_comparison = DistributionComparison(
        chi_square_statistic=round(vr.chi_square_statistic, 6),
        p_value=round(vr.p_value, 6),
        note=vr.note,
    )

    # Journey stats
    stats_baseline = _journey_stats(baseline_result.journeys, baseline_result.stop_nodes)
    stats_whatif = _journey_stats(whatif_result.journeys, whatif_result.stop_nodes)
    completion_delta = round(
        stats_whatif.completion_rate - stats_baseline.completion_rate, 4
    )

    return WhatIfResult(
        baseline_probabilities=baseline_probs,
        whatif_probabilities=whatif_probs,
        deviations=deviations,
        distribution_comparison=dist_comparison,
        journey_stats_baseline=stats_baseline,
        journey_stats_whatif=stats_whatif,
        completion_delta=completion_delta,
    )
