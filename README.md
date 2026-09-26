# TRACR

A developer-focused application maintenance and debugging tool. TRACR
instruments a running application, collects behavioral events, computes a
transition-based behavioral model from real user sessions, and surfaces the
results through a local developer dashboard.

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+

Each numbered step requires its **own terminal opened at the repository root**,
unless noted otherwise.

```bash
# Terminal 1 — API (keep running)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Pre-populate 30 demo sessions (exits when complete)
node sample_project/seed.js

# Terminal 3 — Sample e-commerce app (keep running; open http://localhost:3000)
cd sample_project && python -m http.server 3000

# Terminal 4 — Developer dashboard (keep running; open http://localhost:5173)
cd frontend && npm install && npm run dev   # npm install: first time only
```

## What You'll See

- A **behavioral transition graph** showing which pages users visit and how
  frequently they transition between them, with probabilities on each edge.
- A **ranked flow table** showing the most common complete session paths.
- A **live event feed** showing individual events as they arrive.
- A **summary bar** with total session and event counts.
- **5-second auto-refresh** — the dashboard updates without any manual action.

## Project Structure

```
app/
  api/         FastAPI backend — event collection and analysis endpoints
  twin/        Behavioral Intelligence — graph, transitions, simulator (Person A)
  analysis/    Analysis stubs — anomaly detection, flow analysis (Person A, not yet implemented)
sample_project/
  index.html   Sample e-commerce SPA (Home → Product → Cart → Checkout → Confirmation)
  tracr.js     TRACR instrumentation snippet
  seed.js      Demo data generator — sends 30 pre-scripted sessions
frontend/      React/Vite developer dashboard
data/          Runtime data directory — events.jsonl written here by /collect
docs/          Documentation
tests/         BI layer test suite (Person A)
```

## Documentation

| Document | Contents |
|----------|----------|
| [docs/problem.md](docs/problem.md) | The developer workflow problem TRACR addresses |
| [docs/architecture.md](docs/architecture.md) | System design, data flow, API reference, component map |
| [docs/workflow.md](docs/workflow.md) | Demo script, dashboard tour, step-by-step walkthrough |
| [docs/bob-workflow.md](docs/bob-workflow.md) | How IBM Bob 2.0 was used during development |

## Current Limitations

- **Anomaly detection is not yet implemented.** The `/anomalies` endpoint exists
  and returns an empty list. The analysis module is designed for a future
  milestone.
- **Localhost only.** No authentication, no scaling, no external services.
- **Event file storage.** Events are appended to a plain JSONL file on disk.
  This is intentional for the hackathon scope.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/collect` | Receive a behavioral event from the JS snippet |
| `GET` | `/graph` | Behavioral transition graph (nodes + edges + probabilities) |
| `GET` | `/flows` | Top user journeys ranked by frequency |
| `GET` | `/anomalies` | Anomalies (empty in current MVP) |
| `GET` | `/summary` | Session/event counts and last-updated timestamp |
| `GET` | `/events` | Most recent 100 raw events |
| `GET` | `/health` | Liveness check |

Auto-generated interactive API docs: `http://localhost:8000/docs`
