# TRACR MVP Plan

## Top-Level Overview

TRACR is a developer-focused application maintenance and debugging tool. The
MVP demonstrates a complete developer workflow loop:

1. A sample e-commerce app instruments user behavior via a JS snippet
2. Events are collected by a FastAPI backend and written to a `.jsonl` file on disk
3. A Behavioral Intelligence (BI) layer (owned by the other developer) reads
   that file and produces a behavioral graph with transition probabilities
4. The FastAPI backend exposes that analysis through clean API endpoints
5. A React (Vite) dashboard visualizes the behavioral graph and lets developers
   explore user flows, spot anomalies, and understand real usage patterns

**Scope constraint:** No databases, no message queues, no cloud services, no
auth. The MVP is a working local demo runnable with two commands: one for the
backend, one for the frontend.

**Ownership boundary:**
- Person B owns: `app/api/`, `frontend/`, `docs/`, `sample_project/`
- Other developer owns: `app/twin/`, `app/analysis/`, `data/`, `tests/`
- The interface between the two sides is a shared `.jsonl` event file and a
  small set of Python contracts (dataclasses/TypedDicts) in `app/api/schema.py`

---

## Repository Layout After MVP

Files Person B will create or populate (do NOT touch the other developer's areas):

```
app/
  main.py                  ← FastAPI app factory + CORS + router mount
  api/
    routes.py              ← all API route handlers
    schema.py              ← shared Pydantic/dataclass contracts (NEW)
    collector.py           ← event ingestion logic (NEW)
frontend/                  ← NEW directory
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx
    api/client.js          ← thin fetch wrapper for all backend calls
    components/
      GraphView.jsx        ← behavioral graph visualization
      FlowTable.jsx        ← top user flows ranked by frequency
      EventFeed.jsx        ← live-ish recent events list
      AnomalyPanel.jsx     ← surface anomalies from BI layer
    pages/
      Dashboard.jsx        ← main developer view
sample_project/            ← NEW directory
  index.html               ← simple e-commerce SPA (Home/Product/Cart/Checkout/Confirmation)
  tracr.js                 ← TRACR instrumentation snippet
  style.css
docs/
  architecture.md          ← system overview and component boundaries
  problem.md               ← problem statement and motivation
  workflow.md              ← developer workflow walkthrough
README.md                  ← quick-start instructions
requirements.txt           ← Python dependencies
data/                      ← created by BI layer; Person B reads from it
  events.jsonl             ← append-only raw event log (written by /collect)
```

---

## API / Interface Boundaries

### Event schema (written by `/collect`, read by BI layer)

Each line in `data/events.jsonl` is a JSON object:

```
{
  "session_id": "string",
  "timestamp":  "ISO-8601 string",
  "page":       "string",   // e.g. "home", "product", "cart", "checkout", "confirmation"
  "event":      "string",   // e.g. "page_view", "add_to_cart", "begin_checkout"
  "properties": {}          // optional extra key/value pairs
}
```

This is the **only coupling point** between Person B's collector and the BI
layer. The BI layer reads this file; it never calls Person B's endpoints.

### BI layer output contract (read by API, written by BI layer)

The BI layer writes its analysis results to `data/analysis.json`. The exact
fields must be confirmed with the other developer before implementation.
The minimum set Person B's API needs to consume is listed below. Additional
fields are welcome but must not break Pydantic parsing (use `model_config =
{"extra": "ignore"}`).

```
data/analysis.json
{
  "graph": {
    "nodes": [{ "id": "page_name", "visit_count": int }],
    "edges": [{ "from": "page_a", "to": "page_b", "probability": float, "count": int }]
  },
  "top_flows": [
    { "path": ["home", "product", "cart", "checkout", "confirmation"], "count": int, "share": float }
  ],
  "anomalies": [
    { "type": "string", "description": "string", "severity": "low|medium|high" }
  ],
  "summary": {
    "total_sessions": int,
    "total_events": int,
    "last_updated": "ISO-8601 string"
  }
}
```

**Coordination note:** Treat this schema as a working draft. Share it with the
other developer early and lock the field names before Sub-Task 3 begins.
Person B's API reads this file; it never calls into BI module internals.

### FastAPI endpoints (consumed by React dashboard)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/collect` | Receive a single event from the JS snippet |
| GET | `/graph` | Return the behavioral graph nodes + edges |
| GET | `/flows` | Return ranked top user flows |
| GET | `/anomalies` | Return detected anomalies |
| GET | `/events` | Return recent raw events (last N, for live feed) |
| GET | `/summary` | Return summary statistics |
| GET | `/health` | Liveness check |

All responses are JSON. No authentication. CORS is open for local development
(configured in FastAPI, not via proxy or extra infrastructure).

The `/collect` endpoint accepts `Content-Type: application/json` POST bodies.

---

## Frontend Screens and Components

### Single-page layout

The dashboard is a single page with a top nav and three main panels:

```
┌─────────────────────────────────────────────────────────┐
│  TRACR  │  [sample app link]                            │
├────────────────────────┬────────────────────────────────┤
│                        │  Top Flows (FlowTable)         │
│  Behavioral Graph      ├────────────────────────────────┤
│  (GraphView)           │  Anomalies (AnomalyPanel)      │
│                        ├────────────────────────────────┤
│                        │  Recent Events (EventFeed)     │
├────────────────────────┴────────────────────────────────┤
│  Summary bar: total sessions / events / last updated    │
└─────────────────────────────────────────────────────────┘
```

### Components

**`GraphView.jsx`**
- Renders nodes (pages) as circles sized by `visit_count`
- Renders edges (transitions) as directed arrows labeled with probability
- Uses D3-force or Recharts-Sankey for layout
- Clicking a node highlights all paths through it

**`FlowTable.jsx`**
- Sorted list of top user journeys
- Each row: path as breadcrumb arrows → count → share percentage
- Highlights the happy path (home→product→cart→checkout→confirmation)

**`AnomalyPanel.jsx`**
- List of detected anomalies from the BI layer
- Color-coded by severity (low/medium/high)
- Empty state: "No anomalies detected" when list is empty

**`EventFeed.jsx`**
- Last 20 raw events from `/events`
- Auto-refreshes every 5 seconds
- Shows: timestamp, session_id (truncated), page, event type

**`Dashboard.jsx`**
- Orchestrates all four components
- Fetches `/graph`, `/flows`, `/anomalies`, `/events`, `/summary` on mount
  and then every 5 seconds via `setInterval`
- Includes a manual **Refresh** button that triggers an immediate re-fetch
- Passes data down as props

**`api/client.js`**
- Single file with one function per endpoint
- All functions use `fetch` against `http://localhost:8000`
- Makes it easy to change the base URL without touching components

---

## Sample Application Flow

The sample app (`sample_project/`) is a minimal SPA that simulates a real
e-commerce experience with enough variety to generate interesting behavioral
data.

### Pages

| Page | Route fragment | Key events fired |
|------|---------------|-----------------|
| Home | `#home` | `page_view` |
| Product | `#product` | `page_view`, `add_to_cart` |
| Cart | `#cart` | `page_view`, `remove_from_cart` |
| Checkout | `#checkout` | `page_view`, `begin_checkout` |
| Confirmation | `#confirmation` | `page_view`, `purchase_complete` |

### Instrumentation snippet (`tracr.js`)

- Auto-fires a `page_view` event whenever the hash changes
- Exposes `window.tracr.track(event, properties)` for manual events
- Generates a `session_id` (random UUID stored in `sessionStorage`)
- POSTs to `http://localhost:8000/collect` as a fire-and-forget fetch
- Gracefully silences network errors so it never breaks the sample app

### Realistic variety

The sample app includes a few deliberate navigation variants to make the
behavioral data interesting:
- A "browse and abandon" path: Home → Product → (back to Home)
- A "cart dropout" path: Home → Product → Cart → Home
- The happy path: Home → Product → Cart → Checkout → Confirmation
- A direct deep-link path: Product → Cart → Checkout

These can be triggered by buttons labeled "Simulate [journey name]" on the
Home page to make demos easy.

---

## Integration Points with Behavioral Intelligence

The two sides are decoupled by two files on disk. Person B never imports from
`app/twin/` or `app/analysis/`.

| Direction | Mechanism |
|-----------|-----------|
| Person B → BI | `data/events.jsonl` (Person B writes, BI reads) |
| BI → Person B | `data/analysis.json` (BI writes, Person B reads) |

### What Person B's API does with `analysis.json`

`app/api/routes.py` reads `data/analysis.json` on each relevant request (or
caches it with a short TTL). It maps the file structure directly to the API
response schema — no business logic, just a pass-through with Pydantic
validation.

### Schema contract file: `app/api/schema.py`

This file defines Pydantic models for both the event payload (incoming) and
the analysis output (outgoing). It is the **single source of truth** for the
data shapes both developers agree on. Changes here require coordination.

```
EventPayload     — shape of a POST /collect body
GraphNode        — { id, visit_count }
GraphEdge        — { from, to, probability, count }
BehaviorGraph    — { nodes: list[GraphNode], edges: list[GraphEdge] }
UserFlow         — { path, count, share }
Anomaly          — { type, description, severity }
AnalysisSummary  — { total_sessions, total_events, last_updated }
AnalysisResult   — the full analysis.json shape
```

### Fallback behavior

If `data/analysis.json` does not exist yet (BI layer hasn't run), all
analysis endpoints return empty-but-valid responses so the dashboard still
loads without crashing.

---

## Developer Workflow (User Perspective)

The intended demo story:

1. **Clone and start**: developer runs `uvicorn app.main:app --reload` and
   `npm run dev` in `frontend/`
2. **Serve the sample app**: they run `python -m http.server 3000` inside
   `sample_project/` and open `http://localhost:3000` in a browser
3. **Generate behavior**: they click through the sample store, or hit one of
   the "Simulate journey" buttons a few times — or run `node seed.js` for
   an instant batch of events
4. **Open the dashboard**: they open `http://localhost:5173` in another tab
5. **See the graph**: the behavioral graph shows which pages users visit and
   with what probability
6. **Spot anomalies**: the anomaly panel surfaces any unusual patterns the BI
   layer detected
7. **Understand flows**: the flow table shows the most common paths ranked by
   frequency
8. **Live feed**: the event feed confirms events are arriving in real time
9. **Iterate**: the developer makes a change to the sample app (e.g. adds a
   new "sale" page), generates more events, refreshes the dashboard, sees the
   graph update

This is the complete loop: instrument → observe → understand → iterate.

---

## Documentation

Three doc files to populate (all currently empty stubs):

**`docs/problem.md`**
- What problem TRACR solves (developer blind spots around real user behavior)
- Why existing tools (logs, APM, analytics) don't fully address it
- The TRACR thesis

**`docs/architecture.md`**
- System diagram (ASCII or Mermaid in the doc)
- Component responsibilities
- Data flow: sample app → /collect → events.jsonl → BI layer → analysis.json → API → dashboard
- Interface contracts (event schema, analysis schema)
- Ownership boundaries

**`docs/workflow.md`**
- Step-by-step developer walkthrough
- Screenshots/descriptions of each dashboard panel
- How to run the sample app and generate demo data
- How to extend TRACR to a real application

**`README.md`**
- Quick-start: prerequisites, install, run backend, run frontend
- One-liner description of TRACR
- Link to docs/

---

## Minimal Dependencies

**`requirements.txt`** (Python)
```
fastapi
uvicorn[standard]
pydantic
```

**`frontend/package.json`** key dependencies:
```
react, react-dom
vite
d3 (for graph layout)
recharts (optional, for flow charts)
```

No database driver, no message queue client, no cloud SDK.

---

## Testing Strategy

Person B does not own `tests/`. However, lightweight manual and smoke tests
are appropriate:

- The `/health` endpoint lets anyone verify the backend is up
- The `data/events.jsonl` file can be inspected directly to confirm events
  are being collected correctly
- `sample_project/seed.js` generates a batch of synthetic events by POSTing
  to `/collect` — the primary way to populate demo data without manual clicks;
  kept entirely in `sample_project/`, no Python imports
- The dashboard's empty states (when `analysis.json` doesn't exist) should be
  visually verified manually
- The other developer can write integration tests against the agreed file
  contracts in `tests/` without needing Person B's endpoints

---

## Recommended Implementation Order

Work proceeds in this order so each step is independently demonstrable:

### Sub-Task 1 — Schema contracts and project scaffolding
**Status:** [x] done

**Intent:** Establish the shared data contracts and get both Python and JS
projects runnable before writing any real logic.

**Expected Outcomes:**
- `app/api/schema.py` exists with all Pydantic models
- `requirements.txt` has FastAPI, uvicorn, pydantic
- `app/main.py` starts a FastAPI app with CORS and mounts the router
- `frontend/` is a working Vite+React scaffold (npm run dev works)
- `data/` directory exists with a `.gitkeep`

**Todo List:**
1. Populate `requirements.txt`
2. Create `app/api/schema.py` with all Pydantic models
3. Populate `app/main.py` with FastAPI app + CORS + router mount
4. Scaffold `frontend/` with `npm create vite@latest`
5. Create `data/.gitkeep`

**Relevant Context:**
- `app/main.py` is empty, `app/api/routes.py` is empty
- Schema models: `EventPayload`, `GraphNode`, `GraphEdge`, `BehaviorGraph`,
  `UserFlow`, `Anomaly`, `AnalysisSummary`, `AnalysisResult`

---

### Sub-Task 2 — Event collection endpoint
**Status:** [x] done

**Intent:** Implement `/collect` so the JS snippet can start sending events and
they land in `data/events.jsonl`. This is the first end-to-end path.

**Expected Outcomes:**
- `POST /collect` accepts an `EventPayload` body
- Events are appended as JSON lines to `data/events.jsonl`
- CORS allows the sample app's origin
- `app/api/collector.py` handles file I/O
- Manual `curl` test produces a line in the file

**Todo List:**
1. Create `app/api/collector.py` with an append function
2. Implement `POST /collect` in `app/api/routes.py`
3. Add `GET /events` (last N lines of events.jsonl) in `routes.py`
4. Add `GET /health` in `routes.py`

**Relevant Context:**
- `data/events.jsonl` must be created if it doesn't exist
- Thread safety: for MVP, simple file append is fine (no concurrent writers
  expected beyond the demo)
- The other developer reads this same file; do not lock or rotate it

---

### Sub-Task 3 — Analysis read endpoints
**Status:** [x] done

**Intent:** Wire the BI pipeline (app/twin/) into the API via a translation
bridge. Compute the behavioral graph, flows, and summary on-demand from
events.jsonl, cached for 5 seconds.

**Implemented:**
- `app/api/bi_bridge.py` — translates EventPayload-shaped dicts to BI Events,
  runs build_journeys → build_graph → compute_probabilities, shapes results
  into Pydantic response models, 5-second TTL cache
- `app/api/schema.py` — EventPayload gains optional `action` and `feature`
  fields (backward-compatible defaults from `event` and `page`)
- `app/api/collector.py` — `read_all_events()` added (unlimited read for pipeline)
- `app/api/routes.py` — GET /graph, GET /flows, GET /anomalies, GET /summary added
- `requirements.txt` — merge conflict resolved; scipy added
- 21/21 tests passing

---

### Sub-Task 4 — Sample application
**Status:** [x] done

**Intent:** Build the minimal e-commerce SPA and the TRACR JS snippet so that
serving the sample app through a local HTTP server immediately starts
generating real events.

**Expected Outcomes:**
- `sample_project/index.html` renders five pages navigable by hash
- `sample_project/tracr.js` auto-fires `page_view` on hash change and
  exposes `window.tracr.track()`
- "Simulate journey" buttons on the home page fire a sequence of events
- Events appear in `data/events.jsonl` within seconds of interaction
- The sample app is served via a small local HTTP server (e.g. Python's
  `http.server` or a `serve` npm script) so origins are clean and CORS
  behaves predictably — do NOT rely on `file://` URLs
- `sample_project/seed.js` is a standalone Node script (or plain browser
  script) that POSTs a batch of synthetic events directly to `/collect`
  so the demo can be pre-populated without manual clicking

**Todo List:**
1. Create `sample_project/tracr.js` with session tracking and POST to /collect
2. Create `sample_project/index.html` with five page sections
3. Create `sample_project/style.css` with minimal styling
4. Add "Simulate journey" buttons (browse-and-abandon, cart-dropout, happy path)
5. Add a `sample_project/serve` instruction or npm script to start the local
   HTTP server (e.g. `python -m http.server 3000` noted in README)
6. Create `sample_project/seed.js` as a standalone seed/demo data script
7. Verify events appear in events.jsonl after clicking through the app

**Relevant Context:**
- The snippet must fire-and-forget (no await, errors silenced)
- session_id is a random UUID stored in sessionStorage
- The base URL for /collect should be configurable (default: http://localhost:8000)
- seed.js is separate from app/api/schema.py — it lives entirely in
  sample_project/ and has no Python dependencies

---

### Sub-Task 5 — React dashboard
**Status:** [x] done

**Intent:** Build the developer dashboard so all the behavioral data is
visually surfaced. This is the main deliverable for the demo.

**Expected Outcomes:**
- Dashboard loads at `http://localhost:5173`
- `GraphView` renders the behavioral graph with nodes and directed edges
- `FlowTable` shows ranked user journeys
- `AnomalyPanel` shows anomalies (or empty state)
- `EventFeed` shows recent events and auto-refreshes every 5 seconds
- Summary bar shows session/event counts
- All components degrade gracefully when API returns empty data

**Todo List:**
1. Create `frontend/src/api/client.js` with one function per endpoint
2. Build `Dashboard.jsx` with data fetching logic
3. Build `GraphView.jsx` using D3-force for layout
4. Build `FlowTable.jsx` as a sortable table
5. Build `AnomalyPanel.jsx` with severity color coding
6. Build `EventFeed.jsx` with 5-second polling
7. Wire everything together in `App.jsx`

**Relevant Context:**
- Base URL for API: `http://localhost:8000` (hardcoded for MVP)
- Use D3 for graph, Recharts optional for flow chart
- Empty states are important — dashboard must work before BI layer runs

---

### Sub-Task 6 — Documentation
**Status:** [x] done

**Intent:** Fill in the three empty doc stubs and the README so any developer
can understand, run, and extend TRACR without asking questions.

**Expected Outcomes:**
- `README.md` has quick-start instructions
- `docs/problem.md` explains the problem TRACR solves
- `docs/architecture.md` describes the system with a data-flow diagram
- `docs/workflow.md` walks through the developer experience step by step

**Todo List:**
1. Write `README.md` (prerequisites, install, run backend, run frontend,
   open sample app, open dashboard)
2. Write `docs/problem.md`
3. Write `docs/architecture.md` with ASCII data-flow diagram
4. Write `docs/workflow.md` with step-by-step walkthrough

**Relevant Context:**
- Keep docs concise — this is a hackathon demo, not a product manual
- architecture.md should include the ownership boundary table

---

## Interface Contract Summary (for coordination with other developer)

This section is the explicit agreement between Person B and the other developer.
Neither side should change these contracts without coordinating.

### Contract 1 — `data/events.jsonl`
- **Written by:** Person B (`/collect` endpoint)
- **Read by:** BI layer
- **Format:** One JSON object per line (JSONL)
- **Fields:** `session_id`, `timestamp`, `page`, `event`, `properties`
- **Lifecycle:** Append-only; never truncated during a session

### Contract 2 — `data/analysis.json`
- **Written by:** BI layer
- **Read by:** Person B (API endpoints)
- **Format:** Single JSON file, overwritten on each analysis run
- **Top-level keys:** `graph`, `top_flows`, `anomalies`, `summary`
- **Lifecycle:** BI layer writes this after processing events.jsonl

### Contract 3 — `app/api/schema.py`
- **Maintained by:** Person B, with coordination
- **Purpose:** Pydantic models that define the exact shape of both contracts
- **Rule:** The BI layer may import from this file for type checking, but
  Person B will not import from `app/twin/` or `app/analysis/`
