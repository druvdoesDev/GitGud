# TRACR Developer Workflow

## The Scenario (Demo)

The following is an illustrative demo scenario, not a diagnosis performed by
TRACR automatically.

> A developer is asked to look into why checkout completion rates seem low in
> the sample e-commerce application. Rather than starting by reading code or
> querying logs, they open TRACR to see what behavioral evidence is already
> captured.

This scenario is used throughout this guide to show what TRACR surfaces and
how a developer can use it.

---

## Running the Demo

### Prerequisites

- Python 3.11+
- Node.js 18+
- All Python dependencies installed: `pip install -r requirements.txt`
- Frontend dependencies installed: `cd frontend && npm install`

### Start all components

Open four terminals from the repository root:

**Terminal 1 — API**
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Seed data** (run once; exits when complete)
```bash
node sample_project/seed.js
```
This sends 30 pre-scripted sessions (15 happy path, 8 browse-and-abandon,
5 cart dropout, 2 direct deep-link) to the API. It is the fastest way to
populate the behavioral graph before a demo.

**Terminal 3 — Sample application**
```bash
cd sample_project
python -m http.server 3000
```
Then open `http://localhost:3000` in a browser.

**Terminal 4 — Developer dashboard**
```bash
cd frontend
npm run dev
```
Then open `http://localhost:5173` in a separate browser tab.

---

## The Dashboard Tour

Once data is populated, the dashboard shows the following panels.

### Status Bar and Summary Strip

At the top of the dashboard:

- A green dot labeled **Connected** confirms the API is reachable. If uvicorn
  is not running, this turns red and an error banner appears.
- The summary strip shows **Sessions**, **Events**, and **Last Updated**.

After running `seed.js`, you should see 30 sessions and approximately 210 events.

### Behavioral Graph (left panel)

The graph shows:

- **Nodes** — each page the sample app contains (home, product, cart, checkout,
  confirmation). Node size reflects visit count.
- **Directed edges** — observed transitions between pages, with the edge label
  showing the transition probability as a percentage.
- **Edge thickness** — thicker edges indicate more transitions (higher raw count).

**What this tells a developer:** In the demo scenario, a developer can see that
most sessions reach the product page but a significant fraction return to home
rather than proceeding to cart. This is observable directly from the graph
without reading any code.

The graph is interactive — nodes can be dragged, and the minimap allows
navigation when the graph is zoomed.

### Top User Flows (upper right)

A ranked table of the most common complete session paths.

Each row shows:
- The ordered sequence of pages visited in that session (as breadcrumb chips)
- The number of sessions that followed exactly that path
- The share of all sessions that path represents

The top-ranked flow is highlighted. In the demo with seed data, the happy path
(`home → product → cart → checkout → confirmation`) accounts for 15 of the 30
seeded sessions (50%).

**What this tells a developer:** The developer can identify which flows are
statistically common and which are edge cases, without having to query a database
or aggregate log lines.

### Anomalies (middle right)

**Current status:** This panel shows "No anomalies detected" for all inputs.
The anomaly detection module (`app/analysis/anomaly_detection.py`) is designed
but not yet implemented. This panel will populate automatically when that module
is implemented by the Behavioral Intelligence team.

### Recent Events (lower right)

A live feed of the last 20 raw events, newest first. Each row shows:
- Timestamp (HH:MM:SS)
- Session ID (first 8 characters)
- Page
- Event name

**What this tells a developer:** This confirms that events are flowing from the
instrumented application through to the API in real time. It also shows the
exact event vocabulary the application is generating.

### Auto-Refresh

The dashboard polls all endpoints every 5 seconds. A manual **↻ Refresh** button
triggers an immediate update and resets the interval.

---

## Generating Events Manually

The sample app at `http://localhost:3000` supports manual journey generation:

1. Open the app in a browser tab.
2. Click **Browse Products** → **Add to Cart** → **Proceed to Checkout** → **Place Order** to complete a happy-path journey. Each navigation and action fires one or more events.
3. On the Home page, use the **Demo Controls** box to trigger scripted journeys:
   - **Simulate Happy Path** — replays the full checkout flow with 350ms between steps
   - **Simulate Browse & Abandon** — home → product → home
   - **Simulate Cart Dropout** — home → product → cart → home

Each simulation button creates a **new session ID**, so every click registers
as a separate user session in the behavioral analysis.

After generating events, wait up to 5 seconds or click **↻ Refresh** on the
dashboard to see the updated graph and flows.

---

## Completing the Loop

The developer workflow TRACR targets has this shape:

```
1. Receive a maintenance or debugging question
2. Open TRACR dashboard
3. Read the behavioral graph — which paths are common?
4. Read the flow table — what share of sessions take the expected path?
5. Inspect the event feed — are events arriving correctly?
6. Make a change to the application
7. Generate new behavioral data
8. Refresh the dashboard — did the graph change as expected?
```

To demonstrate step 6–8 with the sample app: add a new page section to
`sample_project/index.html` (e.g. a "Sale" page), link to it from the home
page, and run `node sample_project/seed.js` again with a modified journey
template. The new page node and its edges will appear in the graph on the next
refresh.

---

## Manual Verification Checklist

Use this checklist to confirm all components are working before a demo:

- [ ] **Empty state**: load the dashboard before running `seed.js` — all panels
  show "No data yet" messages, no JavaScript errors in the browser console
- [ ] **Data loads**: run `node sample_project/seed.js`, click ↻ Refresh —
  graph shows 5 nodes with edges and probability labels; flow table shows
  ranked paths; summary bar shows 30 sessions
- [ ] **Auto-refresh**: navigate the sample app, wait 5–6 seconds — event feed
  updates without clicking Refresh
- [ ] **Manual refresh**: click ↻ Refresh — data updates immediately
- [ ] **API-down state**: stop uvicorn (Ctrl-C in Terminal 1) — StatusBar turns
  red and a yellow error banner appears with instructions
