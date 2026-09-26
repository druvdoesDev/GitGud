"""
TRACR Behavioral Intelligence — Virtual-User Simulator.

Generates synthetic user journeys by sampling a TransitionMatrix using
weighted random choices.  Stop nodes are discovered automatically from the
matrix (any node with no outgoing row is terminal); callers may also supply
an explicit extra set to force early termination at specific nodes.

Also provides compare_distributions() which computes an informational
chi-square divergence metric between real and simulated journey edge
distributions.  Requires scipy (Sub-Task 3b).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from scipy import stats as _scipy_stats

from app.twin.behavior_model import TransitionMatrix


@dataclass
class SimulationResult:
    """The output of a single simulate() call."""

    journeys: list[list[str]]
    start_node: str
    max_steps: int
    n_journeys: int
    # Effective stop nodes used during this simulation run
    # (auto-discovered terminal nodes ∪ extra_stop_nodes).
    stop_nodes: list[str]


def simulate(
    matrix: TransitionMatrix,
    start_node: str,
    n_journeys: int,
    max_steps: int,
    extra_stop_nodes: set[str] | None = None,
    rng_seed: int | None = None,
) -> SimulationResult:
    """Generate synthetic user journeys by sampling a TransitionMatrix.

    Parameters
    ----------
    matrix:
        A TransitionMatrix produced by ``compute_probabilities()``.
    start_node:
        The node label every simulated journey begins at.
    n_journeys:
        Number of independent journeys to generate.
    max_steps:
        Hard cap on the number of nodes in a single journey (inclusive of
        ``start_node``).  A journey that reaches this length is terminated
        even if the current node has outgoing transitions.
    extra_stop_nodes:
        Optional set of node labels that force journey termination when
        reached, in addition to the automatically discovered terminal nodes.
    rng_seed:
        Integer seed for ``random.Random``.  Pass the same seed to get
        identical results across calls.  ``None`` (default) → non-reproducible.

    Returns
    -------
    SimulationResult

    Notes
    -----
    Termination priority per step:
      1. Current node is in ``stop_nodes``   → end journey.
      2. Path length has reached ``max_steps``  → end journey.
      3. Current node has no outgoing transitions (dead-end) → end journey.
    """
    # --- Auto-discover terminal nodes ----------------------------------------
    # Any node present in matrix.nodes but absent from matrix.probabilities has
    # no outgoing edges and is therefore a natural journey terminator.
    auto_stop: set[str] = {
        node for node in matrix.nodes if node not in matrix.probabilities
    }
    stop_nodes: set[str] = auto_stop | (extra_stop_nodes or set())

    # --- Pre-compute ordered successor lists for O(1) choices ----------------
    # random.choices needs parallel sequences: population and weights.
    successors: dict[str, tuple[list[str], list[float]]] = {}
    for from_node, row in matrix.probabilities.items():
        nodes_list = list(row.keys())
        weights_list = [row[n] for n in nodes_list]
        successors[from_node] = (nodes_list, weights_list)

    # --- Simulate ------------------------------------------------------------
    rng = random.Random(rng_seed)
    journeys: list[list[str]] = []

    for _ in range(n_journeys):
        path: list[str] = [start_node]

        while True:
            current = path[-1]

            # Termination check 1: stop node
            if current in stop_nodes:
                break

            # Termination check 2: max steps reached
            if len(path) >= max_steps:
                break

            # Termination check 3: dead-end (no successors in matrix)
            if current not in successors:
                break

            pop, weights = successors[current]
            next_node = rng.choices(pop, weights=weights, k=1)[0]
            path.append(next_node)

        journeys.append(path)

    return SimulationResult(
        journeys=journeys,
        start_node=start_node,
        max_steps=max_steps,
        n_journeys=n_journeys,
        stop_nodes=sorted(stop_nodes),
    )


# ---------------------------------------------------------------------------
# Distribution comparison (Sub-Task 3b)
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """Informational comparison between real and simulated edge distributions.

    This report is a diagnostic tool for the developer dashboard.
    It carries no pass/fail judgement — chi-square statistics derived from
    small or demo datasets are not statistically reliable.
    """

    # Normalised edge probability distributions (edge = (from_node, to_node))
    observed_frequencies: dict[tuple[str, str], float]
    simulated_frequencies: dict[tuple[str, str], float]
    # Divergence metric — informational only
    chi_square_statistic: float
    p_value: float
    # Human-readable interpretation for the developer dashboard
    note: str


def _count_edges(journeys: list[list[str]]) -> dict[tuple[str, str], int]:
    """Count every consecutive (from, to) pair across a list of node-label journeys."""
    counts: dict[tuple[str, str], int] = {}
    for journey in journeys:
        for i in range(len(journey) - 1):
            edge = (journey[i], journey[i + 1])
            counts[edge] = counts.get(edge, 0) + 1
    return counts


def _normalise_counts(counts: dict[tuple[str, str], int]) -> dict[tuple[str, str], float]:
    """Convert raw edge counts to a probability distribution (sums to 1.0)."""
    total = sum(counts.values())
    if total == 0:
        return {edge: 0.0 for edge in counts}
    return {edge: c / total for edge, c in counts.items()}


def compare_distributions(
    real_journeys: list[list[str]],
    simulated_journeys: list[list[str]],
) -> ValidationReport:
    """Compare the edge-transition distributions of real and simulated journeys.

    Counts every consecutive (from_node, to_node) transition in each journey
    set, normalises to probability distributions, and computes a chi-square
    goodness-of-fit statistic.

    The result is **informational only**.  With small or demo datasets a
    chi-square test is statistically misleading — low p-values do not mean
    the model is wrong.  The ``note`` field provides a plain-English
    interpretation suitable for display on the developer dashboard.

    Parameters
    ----------
    real_journeys:
        List of journeys from real user data; each journey is a list of
        node-label strings (e.g. the output of ``build_journeys`` projected
        through a ``GraphKey``).
    simulated_journeys:
        List of journeys produced by ``simulate()``, accessed as
        ``SimulationResult.journeys``.

    Returns
    -------
    ValidationReport
        Contains normalised frequency dicts, chi-square statistic, p-value,
        and a human-readable note.  No ``passed`` field.

    Notes
    -----
    Alignment strategy: the union of all edges observed in *either* set is
    used as the full edge vocabulary.  Missing edges in a set are filled with
    count 0 before normalisation.  Because ``scipy.stats.chisquare`` requires
    non-zero expected values, any edge with zero total observed count in the
    *real* distribution is excluded from the test (it contributes nothing to
    the reference distribution).  Edges present in real but absent from
    simulated are included (contributing to the statistic via their deviation).
    """
    real_counts = _count_edges(real_journeys)
    sim_counts = _count_edges(simulated_journeys)

    # Union of all edges seen in either set
    all_edges: list[tuple[str, str]] = sorted(
        real_counts.keys() | sim_counts.keys()
    )

    if not all_edges:
        # No transitions at all — return a zero-statistic report
        return ValidationReport(
            observed_frequencies={},
            simulated_frequencies={},
            chi_square_statistic=0.0,
            p_value=1.0,
            note="No transitions found in either journey set — nothing to compare.",
        )

    # Build aligned raw count arrays over the full edge vocabulary
    real_vec  = [real_counts.get(e, 0) for e in all_edges]
    sim_vec   = [sim_counts.get(e, 0)  for e in all_edges]

    # Exclude edges where the observed (real) count is zero so that
    # the expected array passed to chisquare contains no zeros.
    filtered_edges = [
        e for e, rc in zip(all_edges, real_vec) if rc > 0
    ]
    f_obs = [sim_counts.get(e, 0)  for e in filtered_edges]
    f_exp = [real_counts.get(e, 0) for e in filtered_edges]

    # Scale f_exp to the same total as f_obs so chisquare compares shapes,
    # not magnitudes.
    total_obs = sum(f_obs)
    total_exp = sum(f_exp)

    if total_obs == 0 or total_exp == 0:
        # One set has no transitions at all — statistic is undefined
        chi2, p = 0.0, 1.0
    else:
        scale = total_obs / total_exp
        f_exp_scaled = [v * scale for v in f_exp]
        result = _scipy_stats.chisquare(f_obs=f_obs, f_exp=f_exp_scaled)
        chi2 = float(result.statistic)
        p = float(result.pvalue)

    # Normalised frequency dicts for the report (over the full edge vocab)
    observed_frequencies  = _normalise_counts(real_counts)
    simulated_frequencies = _normalise_counts(sim_counts)

    note = (
        f"chi\u00b2={chi2:.4f}, p={p:.4f} \u2014 informational only; "
        f"small datasets will naturally show low p-values."
    )

    return ValidationReport(
        observed_frequencies=observed_frequencies,
        simulated_frequencies=simulated_frequencies,
        chi_square_statistic=chi2,
        p_value=p,
        note=note,
    )
