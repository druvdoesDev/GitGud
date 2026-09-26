# TRACR — Development with IBM Bob 2.0

## Overview

TRACR was developed using IBM Bob 2.0 as the primary development environment.
The full development process — from initial planning through to a working
end-to-end demo — was conducted within Bob, with a human developer (Person B)
providing direction, approval, and coordination at each stage.

This document describes how Bob was used, what workflow patterns emerged, and
what was and was not delegated to Bob.

---

## Development Structure

The project was divided into six bounded sub-tasks:

| Sub-task | Scope |
|----------|-------|
| 1 | Shared schema contracts and project scaffolding |
| 2 | Event collection API (`POST /collect`, `GET /events`, `GET /health`) |
| 3 | Behavioral analysis endpoints and BI bridge layer |
| 4 | Sample e-commerce application and instrumentation |
| 5 | React/Vite developer dashboard |
| 6 | Documentation |

Each sub-task had an explicit "plan first, implement later" gate. No code was
written until the plan for that sub-task was reviewed and approved.

---

## Plan Mode

Bob's Plan mode was used before any sub-task implementation began.

**Repository inspection before planning:** Bob inspected the existing repository
(initially all empty file stubs) before proposing any changes. This grounded
every proposal in the actual state of the codebase rather than assumptions.

**Clarifying questions:** Plan mode surfaced design decisions that would have
otherwise been assumed. Examples:

| Question asked | Decision made |
|---------------|---------------|
| What should the sample application be? | E-commerce SPA (Home/Product/Cart/Checkout/Confirmation) |
| What framework for the backend API? | FastAPI |
| What framework for the frontend? | React with Vite |
| How should events reach the API from the JS snippet? | `Content-Type: application/json` POST; CORS in FastAPI |
| Where to store events? | Append-only JSONL file on disk |
| Should the sample app open as `file://` or via a server? | Served via `python -m http.server` to ensure clean CORS origins |
| Should each simulation run share or replace the session ID? | Each simulation creates a fresh `session_id` via `newSessionId()` |
| How to scaffold the React frontend? | Handwritten minimal scaffold rather than `npm create vite@latest` |
| Which graph library for the behavioral visualization? | `@xyflow/react` — smallest practical React graph library for the use case |
| How to translate between `EventPayload` fields and BI `Event` fields? | Direct dataclass construction in `bi_bridge.py`, bypassing `normalise()` |

**Plan file:** Each planning session produced or updated `tracr-mvp-plan.md`,
which contains all six sub-task definitions, their expected outcomes, todo
lists, and completion status. This file was updated after each sub-task
completed. It is present in the repository at `tracr-mvp-plan.md`.

**Ownership boundaries:** The two-developer split (Person A: BI layer, Person B:
API/frontend) was established in the plan and respected throughout. Bob was
instructed not to modify `app/twin/`, `app/analysis/`, `data/`, or `tests/`,
and consistently enforced this boundary across all sub-tasks.

---

## Agent Mode

Each approved sub-task was handed to Bob's Agent mode for implementation.

**Repository inspection before each task:** Agent mode re-read the relevant
files at the start of every sub-task to confirm the current state before making
changes. No assumptions were made about file contents.

**Minimal targeted changes:** Bob made only the changes required by the current
sub-task. Surrounding files were not refactored or renamed.

**Inline verification:** Each sub-task included non-blocking verification
commands run within the same agent session:

- Sub-tasks 1–3: Python inline scripts using `fastapi.testclient.TestClient`
  with temporary file paths to verify API behaviour without a running server.
  These are documented in the session history but not committed as test files.
- Sub-task 4: Static file inspection + API round-trip tests for the sample
  application event shapes.
- Sub-task 5: `npm run build` in `frontend/` — confirmed a clean production
  build (201 modules, no errors, output in `frontend/dist/`).
- Backend test suite: the BI developer's test suite in `tests/` covers the
  behavioral intelligence layer independently.

**Verification results that can be stated with confidence:**

- The backend application imports without error:
  `python -c "from app.main import app; print(app.title)"` produces `TRACR`.
- All Pydantic models in `app/api/schema.py` parse correctly including
  alias handling (`GraphEdge` `from`/`to` fields) and extra-field ignoring.
- The frontend production build completes successfully:
  `cd frontend && npm run build` — 201 modules transformed, no errors.
- The BI test suite passes (run by Person A independently).

---

## What Was Not Delegated to Bob

- **Behavioral Intelligence design and implementation** — the `app/twin/` and
  `app/analysis/` modules were designed and implemented by Person A
  independently. Bob had no visibility into or influence over this work.
- **Final integration decisions** — the specific field mappings between
  `EventPayload` and the BI `Event` dataclass were a coordination decision
  between the two developers. Bob surfaced the mismatch (in the Sub-task 3
  planning session) and proposed the resolution; Person B approved it.
- **Repository commits** — all commits were made by the human developer.
  Bob was instructed not to commit at any point.

---

## Impact Measurement

TRACR does not make specific claims about time savings or productivity
percentages, as no controlled comparison was conducted. The following
quantities are relevant and could be measured in a follow-up study:

**Per-sub-task observable quantities:**
- Number of files changed per sub-task (bounded by the plan's todo list)
- Number of verification iterations before a sub-task was approved
- Whether any sub-task required reverting or re-implementing a change

**Developer workflow observable quantities (the problem TRACR addresses):**
- Time to reconstruct a user journey without TRACR (using logs, code, etc.)
- Number of sources consulted per investigation
- Time from "I have a question about user behavior" to "I have an answer"

These quantities are described in [`docs/problem.md`](problem.md) as the
design targets for TRACR's measurement framework, not as resolved results.

---

## Current Limitations Relevant to Bob Usage

- Bob operates within a single context window. Very long sessions (e.g.
  Sub-task 3 which involved reading six BI implementation files plus writing
  the bridge layer) required careful management of context. The plan file
  (`tracr-mvp-plan.md`) served as persistent shared state across sessions.
- Bob could not run a live uvicorn server and issue HTTP requests to it within
  the same command execution, so all API verification used `TestClient` (an
  in-process ASGI test client) rather than real HTTP.
