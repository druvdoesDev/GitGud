# TRACR Architecture

## System Overview

TRACR is a local developer tool that instruments a running application, collects
behavioral events, computes transition-based behavioral analysis, and surfaces
the results through a developer dashboard. All components run locally with no
external services, databases, or authentication.

## Data Flow

```
Browser (sample app at :3000)
  │
  │  1. User navigates: hashchange fires page_view
  │  2. User interacts: add_to_cart, begin_checkout, etc.
  │
  ▼
sample_project/tracr.js
  │  - Generates session_id (UUID in sessionStorage)
  │  - POSTs JSON to POST /collect
  │
  ▼
FastAPI API (app/main.py, app/api/routes.py)  :8000
  │  - Validates EventPayload via Pydantic
  │  - Appends one JSON line to data/events.jsonl
  │
  ▼
data/events.jsonl  (append-only JSONL on disk)
  │
  ▼
app/api/bi_bridge.py  (translation + analysis layer)
  │  - Reads all events from events.jsonl (no limit)
  │  - Translates raw dicts → BI Event dataclasses
  │  - Calls app/twin/behavior_model.py → build_journeys()
  │  - Calls app/twin/transitions.py  → build_graph(key="screen")
  │  - Calls app/twin/transitions.py  → compute_probabilities()
  │  - Caches result for 5 seconds (matches dashboard refresh interval)
  │
  ▼
FastAPI analysis endpoints
  GET /graph      → behavioral transition graph
  GET /flows      → top user journeys ranked by frequency
  GET /anomalies  → [ ] (empty — analysis module not yet implemented)
  GET /summary    → session/event counts, last-updated timestamp
  GET /events     → most recent 100 raw events
  GET /health     → liveness check
  │
  ▼
React dashboard (frontend/ via Vite)  :5173
  │  - Fetches all endpoints on mount, then every 5 seconds
  │  - Manual Refresh button resets the interval
  │
  ├── GraphView   — @xyflow/react behavioral graph
  ├── FlowTable   — ranked user journey table
  ├── AnomalyPanel — anomaly list (empty state only, current MVP)
  ├── EventFeed   — last 20 events, newest first
  ├── SummaryBar  — sessions / events / last-updated
  └── StatusBar   — API connectivity indicator
```

## Component Responsibilities

| File / Directory | Responsibility | Owner |
|------------------|---------------|-------|
| `app/main.py` | FastAPI app factory, CORS configuration, router mount | Person B |
| `app/api/routes.py` | All API route handlers | Person B |
| `app/api/schema.py` | Pydantic models — shared data contracts | Person B (coordinated) |
| `app/api/collector.py` | JSONL read/write helpers | Person B |
| `app/api/bi_bridge.py` | Translation layer: raw events → BI pipeline → API response models | Person B |
| `app/twin/behavior_model.py` | `Event`, `BehavioralGraph`, `TransitionMatrix` dataclasses; `normalise()`, `build_journeys()` | Person A |
| `app/twin/transitions.py` | `build_graph()`, `compute_probabilities()` | Person A |
| `app/twin/simulator.py` | `simulate()`, `compare_distributions()`, `SimulationResult`, `ValidationReport` | Person A |
| `app/analysis/anomaly_detection.py` | Stub — not yet implemented | Person A |
| `app/analysis/feature_usage.py` | Stub — not yet implemented | Person A |
| `app/analysis/user_flows.py` | Stub — not yet implemented | Person A |
| `data/events.jsonl` | Append-only event log (created on first `/collect` call) | Shared |
| `sample_project/` | Demo e-commerce SPA + TRACR instrumentation + seed script | Person B |
| `frontend/` | React/Vite developer dashboard | Person B |
| `tests/` | BI layer test suite | Person A |

## Ownership Boundaries

Two developers worked on TRACR independently during the hackathon:

| Area | Owner | Files |
|------|-------|-------|
| Behavioral Intelligence | Person A | `app/twin/`, `app/analysis/`, `data/`, `tests/` |
| API, Frontend, Sample App | Person B | `app/api/`, `frontend/`, `docs/`, `sample_project/` |

The two sides are decoupled by shared data contracts in `app/api/schema.py`.
Neither side imports from the other's private modules (with the single
exception of `bi_bridge.py`, which calls the public functions in `app/twin/`
as a read-only caller).

## Integration Contracts

### Contract 1 — `data/events.jsonl`

Written by the `/collect` endpoint; readable by any component.

Each line is a JSON object with these fields:

```json
{
  "session_id":  "string  — client UUID from sessionStorage",
  "timestamp":   "ISO-8601 string",
  "page":        "string  — e.g. home | product | cart | checkout | confirmation",
  "event":       "string  — e.g. page_view | add_to_cart | purchase_complete",
  "properties":  "object  — optional free-form metadata",
  "action":      "string  — defaults to event value if absent",
  "feature":     "string  — defaults to page value if absent"
}
```

### Contract 2 — `app/api/schema.py`

Pydantic models that define the exact shape of both inbound events and
outbound API responses. Both Person A and Person B may import from this file.
Changes require coordination.

Key models: `EventPayload`, `GraphNode`, `GraphEdge`, `BehaviorGraph`,
`UserFlow`, `Anomaly`, `AnalysisSummary`, `AnalysisResult`.

## API Reference

| Method | Path | Description | Response shape |
|--------|------|-------------|----------------|
| `POST` | `/collect` | Receive a behavioral event | `{status, session_id, event, page}` |
| `GET` | `/graph` | Behavioral transition graph | `{nodes:[{id,visit_count}], edges:[{from,to,probability,count}]}` |
| `GET` | `/flows` | Top user journeys ranked by frequency | `{flows:[{path,count,share}]}` |
| `GET` | `/anomalies` | Detected anomalies (empty in current MVP) | `{anomalies:[]}` |
| `GET` | `/summary` | Session/event counts and last-updated | `{total_sessions,total_events,last_updated}` |
| `GET` | `/events` | Most recent 100 raw events | `{events:[...],count}` |
| `GET` | `/health` | Liveness check | `{status:"ok"}` |

CORS is configured in `app/main.py` for `http://localhost:5173` (dashboard)
and `http://localhost:3000` (sample app). No authentication.

## Performance Notes

- `bi_bridge.get_analysis()` caches the full analysis result for 5 seconds.
  All four analysis endpoints (`/graph`, `/flows`, `/anomalies`, `/summary`)
  share this cache, so a dashboard refresh cycle triggers at most one full
  pipeline run regardless of how many panels load simultaneously.
  (`/events` reads `events.jsonl` directly and does not use this cache.)
- Event file I/O is synchronous. For a local demo with one writer at a time
  this is adequate. The file is never locked or rotated.

## What Is Not Yet Wired

- `app/analysis/anomaly_detection.py` — empty stub. The `GET /anomalies`
  endpoint returns `[]` until this module is implemented.
- `app/analysis/feature_usage.py` — empty stub.
- `app/analysis/user_flows.py` — empty stub.
- `app/twin/simulator.py` implements `simulate()` and `compare_distributions()`
  but these are not currently called by any API endpoint.
