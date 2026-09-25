# TRACR — Behavioral Intelligence MVP Plan

## Top-Level Overview

**Goal:** Build the first working slice of TRACR's Behavioral Intelligence layer — from raw user journey events through to a simple virtual-user simulator — using only plain Python data structures and standard-library/lightweight libraries.

**Scope (MVP Milestone 1):**

```
user journey events  [JSON/dict from any of 3 sources]
      ↓
event model  [normalise into canonical Event]
      ↓
behavioral graph  [configurable node key: screen | action | feature]
      ↓
transition counts
      ↓
transition probabilities
      ↓
simple virtual-user simulation
      ↓
distribution comparison report  [informational, not a pass/fail gate]
```

**Non-goals for this milestone:**
- Anomaly detection (designed for later extension, not implemented)
- Feature usage analysis (same)
- User-flow analysis (same)
- Any database, message bus, cloud infrastructure
- Frontend / API routes (API interfaces are data-only contracts, not implemented here)
- Files outside `app/twin/`, `app/analysis/`, `data/`, `tests/`

**Ownership boundary:** Person A owns `app/twin/`, `app/analysis/`, `data/`, `tests/`. Do NOT touch `app/api/`, `frontend/`, `docs/`, `sample_project/`.

---

## Data Structures

### 1. Event

The normalised internal representation of a single user interaction. All sources (frontend instrumentation, backend logs, test fixtures) produce this after parsing.

```
Event
  user_id:    str          — opaque identifier for the session/user
  timestamp:  float        — Unix epoch seconds (float for ms precision)
  event_type: str          — e.g. "page_view", "click", "api_call", "error"
  screen:     str          — logical screen or route name
  action:     str          — what the user did ("submit_form", "click_nav", …)
  feature:    str          — feature area ("search", "checkout", "onboarding", …)
  metadata:   dict         — arbitrary extra fields (source-specific, not required)
```

All fields except `metadata` are required. `metadata` defaults to `{}`.

### 2. Journey

An ordered sequence of Events belonging to a single user session. Represented as `list[Event]`, sorted ascending by timestamp. The pair of consecutive events `(events[i], events[i+1])` is one **transition**.

### 3. GraphKey

A `Literal["screen", "action", "feature"]` string. Configures which event field becomes a node in the behavioral graph.

### 4. BehavioralGraph

```
BehavioralGraph
  key:              GraphKey
  transition_counts: dict[str, dict[str, int]]
      outer key = "from" node label
      inner key = "to" node label
      value     = count of observed transitions
  node_counts:      dict[str, int]
      key   = node label
      value = number of times this node was entered
```

### 5. TransitionMatrix

```
TransitionMatrix
  key:          GraphKey
  probabilities: dict[str, dict[str, float]]
      — same shape as transition_counts but values are probabilities (sum to 1.0 per row)
  nodes:        list[str]   — sorted node list for display / matrix indexing
```

### 6. SimulationResult

```
SimulationResult
  journeys:        list[list[str]]   — each inner list is a sequence of node labels
  start_node:      str               — node used as starting point
  max_steps:       int               — cap on journey length
  n_journeys:      int               — number of simulated journeys
  stop_nodes:      list[str]         — effective stop nodes used (auto-discovered + any extras)
```

### 7. ValidationReport

```
ValidationReport
  observed_frequencies:  dict[tuple[str,str], float]   — empirical edge probabilities from real journeys
  simulated_frequencies: dict[tuple[str,str], float]   — edge probabilities from simulated journeys
  chi_square_statistic:  float                          — divergence metric (informational only)
  p_value:               float                          — informational only; not used as a gate
  note:                  str                            — human-readable interpretation for the dashboard
```

`ValidationReport` carries no `passed` field. The chi-square statistic is a diagnostic metric shown to
the developer, not a correctness criterion. Small datasets will naturally produce low p-values.

---

## Core Algorithms

### A. Event Normalisation

```
normalise(raw: dict, source: str = "default") -> Event
```

- Accepts a raw Python dict. All three supported sources deliver JSON/dict input — no live HTTP ingestion in the MVP.
- Three supported `source` values, each with its own field-name mapping table:
  - `"frontend"` — browser beacon shape: `userId`, `ts`, `type`, `page`, `action`, `feature`, `meta`
  - `"backend"` — server log shape: `uid`, `time`, `kind`, `route`, `op`, `area`, `extra`
  - `"default"` — canonical shape already matching Event fields; used for test fixtures and direct ingestion
- After applying the mapping, validates that all six required fields are non-empty strings/floats.
- Raises `ValueError` naming the missing field if validation fails.
- Returns an `Event`.

### B. Journey Builder

```
build_journeys(events: list[Event]) -> dict[str, list[Event]]
```

- Groups events by `user_id`.
- Sorts each group ascending by `timestamp`.
- Returns a dict of `user_id → Journey`.

### C. Graph Builder

```
build_graph(journeys: list[list[Event]], key: GraphKey) -> BehavioralGraph
```

- Iterates every consecutive pair `(e_i, e_i+1)` in every journey.
- Extracts the node label from `getattr(event, key)` on each event.
- Increments `transition_counts[from_label][to_label]` and `node_counts`.
- Returns a `BehavioralGraph`.

### D. Probability Calculator

```
compute_probabilities(graph: BehavioralGraph) -> TransitionMatrix
```

- For each source node `s` with outgoing counts, divides each `counts[s][t]` by `sum(counts[s].values())` to get `P(t | s)`.
- Handles the zero-count edge (isolated node) by leaving its row empty or assigning uniform 0.
- Returns a `TransitionMatrix`.

### E. Simulator

```
simulate(
    matrix: TransitionMatrix,
    start_node: str,
    n_journeys: int,
    max_steps: int,
    extra_stop_nodes: set[str] | None = None,
    rng_seed: int | None = None
) -> SimulationResult
```

- Derives `stop_nodes` automatically: any node that appears in `matrix.nodes` but has no outgoing row in `matrix.probabilities` is a natural terminal node. The caller may additionally pass `extra_stop_nodes` to force early termination at specific nodes (e.g. "error", "logout").
- Initialises a `random.Random` with `rng_seed` for reproducibility.
- For each of `n_journeys`: begin at `start_node`, repeatedly sample the next node using `random.choices` with the probability weights for the current node, append to path, stop if the new node is in `stop_nodes` or path length reaches `max_steps`.
- Returns `SimulationResult` (which records the effective `stop_nodes` set used).

### F. Validator

```
compare_distributions(
    real_journeys:       list[list[str]],
    simulated_journeys:  list[list[str]]
) -> ValidationReport
```

- Counts edge frequencies in both sets of journeys and normalises to probability distributions.
- Runs `scipy.stats.chisquare` to compute a divergence metric.
- **The result is informational only.** With small or demo datasets a chi-square test is statistically misleading. `ValidationReport` surfaces the numbers for the dashboard without making any pass/fail judgement.
- Returns `ValidationReport`.

---

## File Changes

### New files to create

| File | Purpose |
|------|---------|
| `data/__init__.py` | Makes `data` a package; houses sample journey fixtures |
| `data/sample_journeys.py` | Example raw event dicts and pre-built Journey fixtures for tests |
| `tests/__init__.py` | Test package marker |
| `tests/test_event_model.py` | Unit tests for Event normalisation |
| `tests/test_graph_builder.py` | Unit tests for journey building and graph construction |
| `tests/test_transitions.py` | Unit tests for probability calculation |
| `tests/test_simulator.py` | Unit tests for simulation and validation |

### Existing files to implement (currently empty)

| File | What goes in it |
|------|----------------|
| `app/twin/behavior_model.py` | `Event` dataclass, `GraphKey` type alias, `BehavioralGraph` dataclass, `TransitionMatrix` dataclass, `normalise()`, `build_journeys()` |
| `app/twin/transitions.py` | `build_graph()`, `compute_probabilities()` |
| `app/twin/simulator.py` | `SimulationResult` dataclass, `ValidationReport` dataclass, `simulate()`, `validate()` |
| `app/analysis/anomaly_detection.py` | Stub only — public interface defined, body `raise NotImplementedError` |
| `app/analysis/feature_usage.py` | Stub only — public interface defined, body `raise NotImplementedError` |
| `app/analysis/user_flows.py` | Stub only — public interface defined, body `raise NotImplementedError` |
| `app/__init__.py` | Package marker (create if missing) |
| `app/twin/__init__.py` | Package marker + public re-exports |
| `app/analysis/__init__.py` | Package marker + public re-exports |
| `requirements.txt` | `scipy` (only external dependency needed for chi-square validation) |

### Do NOT touch

`app/api/routes.py`, `app/main.py`, `docs/`, `frontend/`, `sample_project/`

---

## API Layer Interfaces

These are the data contracts the API layer will eventually call. The implementation lives entirely in `app/twin/` and `app/analysis/`; the API layer only imports and calls them.

```
# Ingest a batch of raw events → normalised events
POST /ingest  →  body: list[dict]  →  returns: list[Event]  (API wraps normalise())

# Build a behavioral graph from journeys
POST /graph   →  body: { events: list[Event], key: GraphKey }
              →  returns: TransitionMatrix

# Run a simulation
POST /simulate →  body: { matrix: TransitionMatrix, start_node, n_journeys, max_steps,
                           extra_stop_nodes?: list[str], rng_seed?: int }
               →  returns: SimulationResult

# Compare simulated distribution against real data (informational)
POST /validate →  body: { real: list[list[str]], simulated: list[list[str]] }
               →  returns: ValidationReport   — chi-square stat + p_value, no pass/fail field
```

The API layer will serialise/deserialise the dataclasses. All dataclasses should support `asdict()` conversion (use `dataclasses.asdict`).

---

## Extension Points (Design for Later, Not Now)

### Anomaly Detection

`app/analysis/anomaly_detection.py` will expose:

```
detect_anomalies(
    matrix: TransitionMatrix,
    journey: list[str],
    threshold: float
) -> list[AnomalyRecord]
```

It compares the probability of each transition in a live journey against the trained `TransitionMatrix`. Low-probability transitions are flagged. No MVP code needed — just the stub with the signature.

### Feature Usage Analysis

`app/analysis/feature_usage.py` will expose:

```
feature_usage_report(journeys: list[list[Event]]) -> FeatureUsageReport
```

Counts how frequently each `feature` field is touched, how many unique users reach it, and average position in journey. Stub only for MVP.

### User-Flow Analysis

`app/analysis/user_flows.py` will expose:

```
top_paths(
    graph: BehavioralGraph,
    n: int
) -> list[PathRecord]

drop_off_points(
    graph: BehavioralGraph
) -> list[DropOffRecord]
```

Identifies the most common multi-hop paths and nodes where journeys end unexpectedly. Stub only for MVP.

---

## Example Input Journeys

### Raw events (before normalisation)

```
Journey 1 — normal checkout flow
  { user_id:"u1", timestamp:1000.0, event_type:"page_view", screen:"home",     action:"view",        feature:"browse",   metadata:{} }
  { user_id:"u1", timestamp:1005.0, event_type:"click",     screen:"product",  action:"view_product", feature:"browse",   metadata:{} }
  { user_id:"u1", timestamp:1020.0, event_type:"click",     screen:"cart",     action:"add_to_cart",  feature:"checkout", metadata:{} }
  { user_id:"u1", timestamp:1040.0, event_type:"page_view", screen:"checkout", action:"view",         feature:"checkout", metadata:{} }
  { user_id:"u1", timestamp:1060.0, event_type:"click",     screen:"confirm",  action:"submit_order", feature:"checkout", metadata:{} }

Journey 2 — browse without purchase
  { user_id:"u2", timestamp:2000.0, event_type:"page_view", screen:"home",    action:"view",         feature:"browse", metadata:{} }
  { user_id:"u2", timestamp:2010.0, event_type:"click",     screen:"search",  action:"search",       feature:"search", metadata:{} }
  { user_id:"u2", timestamp:2025.0, event_type:"click",     screen:"product", action:"view_product", feature:"browse", metadata:{} }
  { user_id:"u2", timestamp:2040.0, event_type:"page_view", screen:"home",    action:"view",         feature:"browse", metadata:{} }

Journey 3 — repeat of journey 1 (to build probability mass)
  (same as Journey 1 but user_id:"u3", timestamps offset by 3000)
```

---

## Expected Behavioral Graph / Probability Output

Using `key="screen"` on the three journeys above:

### Transition counts

Journey breakdown:
- u1: home → product → cart → checkout → confirm
- u2: home → search → product → home
- u3: home → product → cart → checkout → confirm  (repeat of u1)

```
home      → product:  2   (u1, u3)
home      → search:   1   (u2)
product   → cart:     2   (u1, u3)
product   → home:     1   (u2 returns)
cart      → checkout: 2   (u1, u3)
checkout  → confirm:  2   (u1, u3)
search    → product:  1   (u2)
```

Note: an earlier version of this table incorrectly listed `home→product: 3 (u1, u2, u3)`.
u2's first step is `home→search`, not `home→product`. Corrected above.

### Transition probabilities

```
P(product  | home)     = 2/3 ≈ 0.667   (home has 3 total outgoing: product x2, search x1)
P(search   | home)     = 1/3 ≈ 0.333
P(cart     | product)  = 2/3 ≈ 0.667   (product has 3 total outgoing: cart x2, home x1)
P(home     | product)  = 1/3 ≈ 0.333
P(checkout | cart)     = 1.0
P(confirm  | checkout) = 1.0
P(product  | search)   = 1.0
```

### Expected simulator output (start="home", n=100, max_steps=10)

~75% of journeys follow home→product→cart→checkout→confirm
~25% of journeys follow home→search→product→(cart or home)

---

## Test Plan

### `tests/test_event_model.py`

| Test | Verifies |
|------|---------|
| `test_normalise_valid_event` | All required fields present → returns valid Event |
| `test_normalise_missing_required_field` | Missing screen → raises ValueError |
| `test_normalise_metadata_defaults_to_empty` | No metadata key → Event.metadata == {} |
| `test_build_journeys_groups_by_user` | Two users → two journey keys |
| `test_build_journeys_sorted_by_timestamp` | Out-of-order events → sorted in output |

### `tests/test_graph_builder.py`

| Test | Verifies |
|------|---------|
| `test_build_graph_counts_transitions` | Known journeys → expected count dict |
| `test_build_graph_configurable_key` | key="action" vs key="screen" → different graphs |
| `test_build_graph_single_event_journey` | One-event journey → no transitions added |
| `test_build_graph_empty_input` | Empty list → empty graph |
| `test_node_counts_correct` | node_counts match sum of outgoing + entry from start |

### `tests/test_transitions.py`

| Test | Verifies |
|------|---------|
| `test_probabilities_sum_to_one` | Each row of TransitionMatrix sums to 1.0 |
| `test_probabilities_match_counts` | Known counts → expected probability values |
| `test_isolated_node_handled` | Node with no outgoing edges → no row or empty row, no crash |
| `test_deterministic_node` | Only one successor → probability 1.0 |

### `tests/test_simulator.py`

**Simulation tests (no scipy required):**

| Test | Verifies |
|------|---------|
| `test_simulate_reproducible` | Same seed → identical SimulationResult.journeys |
| `test_simulate_different_seeds` | Different seeds → different journey sets |
| `test_simulate_respects_max_steps` | No journey longer than max_steps |
| `test_simulate_auto_discovers_stop_nodes` | Nodes with no outgoing edges are terminal; journeys stop there |
| `test_simulate_extra_stop_nodes` | Explicit extra_stop_nodes forces termination at named node |
| `test_simulate_terminates_on_dead_end` | Isolated node with no successors → single-node journey |
| `test_simulate_stop_nodes_recorded` | SimulationResult.stop_nodes contains auto-discovered set |

**Distribution comparison tests (requires scipy):**

| Test | Verifies |
|------|---------|
| `test_compare_identical_distributions` | Same journeys used for both → chi_square_statistic near 0 |
| `test_compare_divergent_distributions` | Very different journeys → high chi_square_statistic |
| `test_compare_no_passed_field` | ValidationReport has no `passed` attribute |
| `test_compare_returns_note` | ValidationReport.note is a non-empty string |

---

## Recommended Implementation Order

The order is designed so the core demo pipeline is runnable as early as step 5, before validation is added.

1. **`app/twin/behavior_model.py`** — Event dataclass + normalise() (3-source mapping) + build_journeys()
   Prerequisite for everything. No imports from the rest of the codebase.

2. **`data/__init__.py` + `data/sample_journeys.py`** — Fixture data in both raw-dict and Event form.
   Needed by all tests. Pure data, no logic.

3. **`tests/test_event_model.py`** — Tests for step 1 (red → green)

4. **`app/twin/transitions.py`** — build_graph() + compute_probabilities()
   Depends only on behavior_model types.

5. **`tests/test_graph_builder.py` + `tests/test_transitions.py`** — Tests for step 4 (red → green)

6. **`app/twin/simulator.py`** — simulate() with auto-discovered stop nodes. Core demo pipeline complete.
   Depends on transitions.py types. Standard-library only at this step.

7. **`tests/test_simulator.py` (simulation tests only)** — Tests for step 6 (red → green)

8. **`app/twin/simulator.py` — add compare_distributions()** — Add the validator after the core pipeline passes.
   Adds `scipy` as the only new dependency.

9. **`tests/test_simulator.py` (validation tests)** — Tests for step 8 (red → green)

10. **`app/analysis/anomaly_detection.py`, `feature_usage.py`, `user_flows.py`** — Stubs with signatures.
    No logic, just future-proof interfaces.

11. **`app/twin/__init__.py`, `app/analysis/__init__.py`, `app/__init__.py`** — Package markers + re-exports

12. **`requirements.txt`** — Add `scipy`

---

## Sub-Tasks

---

### Sub-Task 1 — Event Model and Journey Builder

**Intent:** Define the canonical `Event` data structure and the functions that normalise raw source data and assemble events into per-user journeys. This is the foundation every other component depends on.

**Expected Outcomes:**
- `app/twin/behavior_model.py` contains `Event`, `GraphKey`, `BehavioralGraph`, `TransitionMatrix`, `normalise()`, `build_journeys()`
- `data/sample_journeys.py` contains the three example journeys from this plan
- `tests/test_event_model.py` passes all tests listed in the test plan

**Todo List:**
1. Add `Event` dataclass with all required fields and `metadata: dict` defaulting to `{}`
2. Add `GraphKey` type alias (`Literal["screen", "action", "feature"]`)
3. Add `BehavioralGraph` and `TransitionMatrix` dataclasses (fields only, no logic)
4. Implement `normalise(raw: dict, source: str = "default") -> Event` with three source mappings:
   - `"frontend"`: `userId→user_id`, `ts→timestamp`, `type→event_type`, `page→screen`, `action→action`, `feature→feature`, `meta→metadata`
   - `"backend"`: `uid→user_id`, `time→timestamp`, `kind→event_type`, `route→screen`, `op→action`, `area→feature`, `extra→metadata`
   - `"default"`: identity mapping (fields already match canonical names)
5. Implement `build_journeys(events: list[Event]) -> dict[str, list[Event]]`
6. Create `data/__init__.py` and `data/sample_journeys.py` with the three example journeys
7. Create `tests/__init__.py`
8. Write `tests/test_event_model.py` covering all tests in the test plan section

**Relevant Context:**
- `app/twin/behavior_model.py` is currently empty
- Event fields: `user_id`, `timestamp`, `event_type`, `screen`, `action`, `feature`, `metadata`
- Use `@dataclass` from `dataclasses` standard library
- `normalise()` supports three sources: `"frontend"`, `"backend"`, `"default"`. No HTTP ingestion.
- `data/sample_journeys.py` should contain raw dicts in all three source shapes so tests exercise all mappings.

**Status:** [x] done — 20 tests passing (see tests/test_event_model.py)

---

### Sub-Task 2 — Graph Builder and Transition Probabilities

**Intent:** Convert a collection of journeys into a `BehavioralGraph` (counts) and then a `TransitionMatrix` (probabilities). The key insight is that node identity is configurable — the same journey data can produce a screen-level graph or an action-level graph.

**Expected Outcomes:**
- `app/twin/transitions.py` contains `build_graph()` and `compute_probabilities()`
- `tests/test_graph_builder.py` and `tests/test_transitions.py` all pass
- Running against the sample journeys produces the exact counts and probabilities shown in this plan

**Todo List:**
1. Implement `build_graph(journeys: list[list[Event]], key: GraphKey) -> BehavioralGraph`
2. Implement `compute_probabilities(graph: BehavioralGraph) -> TransitionMatrix`
3. Write `tests/test_graph_builder.py` covering all tests in the test plan section
4. Write `tests/test_transitions.py` covering all tests in the test plan section
5. Verify output matches the expected counts/probabilities table in this plan using sample_journeys

**Relevant Context:**
- Types are defined in `app/twin/behavior_model.py` (Sub-Task 1 must be complete)
- Node label = `getattr(event, key)` where key is the GraphKey
- `transition_counts` shape: `dict[str, dict[str, int]]`

**Status:** [x] done — 26 new tests passing (test_graph_builder.py: 12, test_transitions.py: 14); full suite 46/46

---

### Sub-Task 3 — Simulator

**Intent:** Build the virtual-user simulator that samples synthetic journeys from a `TransitionMatrix`. Stop nodes are discovered automatically from the graph — any node present in `matrix.nodes` but absent as a key in `matrix.probabilities` is terminal. The caller may also pass `extra_stop_nodes` to force early termination at specific nodes. This keeps the simulator self-contained with no external dependencies.

**Expected Outcomes:**
- `app/twin/simulator.py` contains `SimulationResult` dataclass and `simulate()`
- `simulate()` is reproducible given the same seed
- `SimulationResult.stop_nodes` records which nodes were treated as terminal
- Simulation tests (no scipy) all pass

**Todo List:**
1. Add `SimulationResult` dataclass to `app/twin/simulator.py` (includes `stop_nodes: list[str]`)
2. Implement `simulate()` using `random.Random` and `random.choices` for weighted sampling
3. Auto-discover terminal nodes: `stop_nodes = {n for n in matrix.nodes if n not in matrix.probabilities}`
4. Merge with `extra_stop_nodes` if provided
5. Write simulation tests in `tests/test_simulator.py` (all tests from the "Simulation tests" section of the test plan)

**Relevant Context:**
- `TransitionMatrix` is defined in `app/twin/behavior_model.py` (Sub-Task 1 must be complete)
- `simulate()` signature: `simulate(matrix, start_node, n_journeys, max_steps, extra_stop_nodes=None, rng_seed=None)`
- Termination priority: stop_node check → max_steps check → dead-end (no successors in matrix)
- At this point `requirements.txt` still needs no new entries — scipy is added in Sub-Task 3b

**Status:** [x] done — 23 new tests passing (test_simulator.py simulation section); full suite 69/69

---

### Sub-Task 3b — Distribution Comparison

**Intent:** Add the informational distribution validator to `simulator.py`. This is deliberately kept separate from the core simulator so that the pipeline (events → simulation) is fully demonstrable before scipy is introduced. The validator produces a `ValidationReport` for the developer dashboard — it carries no pass/fail judgement.

**Expected Outcomes:**
- `app/twin/simulator.py` also contains `ValidationReport` dataclass and `compare_distributions()`
- `ValidationReport` has no `passed` field — only `observed_frequencies`, `simulated_frequencies`, `chi_square_statistic`, `p_value`, and `note`
- Distribution comparison tests all pass
- `requirements.txt` updated with `scipy`

**Todo List:**
1. Add `ValidationReport` dataclass (no `passed` field; include `note: str`)
2. Implement `compare_distributions(real_journeys, simulated_journeys) -> ValidationReport`
3. Normalise both edge-count dicts to probability distributions before passing to `scipy.stats.chisquare`
4. Populate `note` with a human-readable string, e.g. `"chi²=X.XX, p=0.YY — informational only, small datasets will show low p-values"`
5. Add `scipy` to `requirements.txt`
6. Write distribution comparison tests in `tests/test_simulator.py`

**Relevant Context:**
- `compare_distributions` must align both frequency dicts to the same edge set before chi-square (add zero counts for missing edges)
- The test `test_compare_no_passed_field` verifies `hasattr(report, "passed") is False`

**Status:** [x] done — 11 new tests passing (test_simulator.py TestCompareDistributions); full suite 80/80

---

### Sub-Task 4 — Analysis Stubs and Package Wiring

**Intent:** Define the public interfaces for the three future analysis modules as documented stubs, and wire all packages together with `__init__.py` files and re-exports. This makes the API layer's eventual imports clean and validates the package structure.

**Expected Outcomes:**
- `app/analysis/anomaly_detection.py`, `feature_usage.py`, `user_flows.py` each have documented function signatures with `raise NotImplementedError`
- `app/__init__.py`, `app/twin/__init__.py`, `app/analysis/__init__.py` exist and re-export public symbols
- `import app.twin.behavior_model` and `import app.twin.simulator` work from project root
- All existing tests continue to pass

**Todo List:**
1. Add stub signatures + docstrings to `app/analysis/anomaly_detection.py`
2. Add stub signatures + docstrings to `app/analysis/feature_usage.py`
3. Add stub signatures + docstrings to `app/analysis/user_flows.py`
4. Create `app/__init__.py` (empty or minimal)
5. Create `app/twin/__init__.py` re-exporting: `Event`, `GraphKey`, `BehavioralGraph`, `TransitionMatrix`, `normalise`, `build_journeys`, `build_graph`, `compute_probabilities`, `SimulationResult`, `ValidationReport`, `simulate`, `validate`
6. Create `app/analysis/__init__.py` re-exporting the three stub functions

**Relevant Context:**
- `AnomalyRecord`, `FeatureUsageReport`, `PathRecord`, `DropOffRecord` return types for stubs can be typed as `dict` for now (or left as `Any`) — full types are future work
- Do NOT add logic to stubs; the point is interface discoverability

**Status:** [ ] pending
