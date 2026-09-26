<div align="center">

TRACR

Behavioral Runtime Intelligence for Developers

Built for the Digital IBM Bob 2.0 Hackathon







Observe → Model → Simulate → Investigate

</div>

🖥️ TRACR at a glance

TRACR is a developer-focused application-maintenance and debugging prototype that turns runtime user behavior into an interactive behavioral model.

Instead of forcing developers to reconstruct user journeys from disconnected logs, TRACR combines:

Runtime events
→ Behavioral graph
→ User-flow analysis
→ What-If simulation
→ Behavioral instability visualization

<div align="center">



Main TRACR investigation dashboard

</div>

<div align="center">



Behavioral Instability view

</div>

🎯 The problem

When an application behaves unexpectedly, developers can see the bug — but often cannot easily see the user behavior that led to it.

Traditional logs are useful for questions such as:

What request failed?

What error occurred?

Which endpoint was called?

But they are much less convenient for questions such as:

What path did users actually take through the application, and what happens to that behavior when I change a transition?

TRACR addresses that gap by turning runtime interaction data into a visual behavioral model that can be explored and stress-tested from one dashboard.

🚀 What we built

1. Runtime event collection

The sample e-commerce application emits lightweight behavioral events such as page views and user actions.

Events are sent to the FastAPI backend and persisted as JSONL.

The sample application follows a simple journey:

Home → Product → Cart → Checkout → Confirmation

The seeded dataset contains multiple journey patterns, including:

happy-path sessions

browsing / abandonment

cart dropouts

deep-link sessions

This gives TRACR enough behavioral variation to demonstrate both common and unusual navigation patterns.

2. Behavioral graph

TRACR transforms observed sessions into a directed behavioral graph.

          ┌─────────┐
          │  Home   │
          └────┬────┘
               │
               ▼
          ┌─────────┐
          │ Product │
          └────┬────┘
               │
               ▼
          ┌─────────┐
          │  Cart   │
          └────┬────┘
               │
               ▼
          ┌─────────┐
          │Checkout │
          └────┬────┘
               │
               ▼
        ┌──────────────┐
        │ Confirmation │
        └──────────────┘

Each node represents an observed screen or page.

Each directed edge represents an observed transition.

For every transition, TRACR exposes:

Signal

Meaning

Transition count

How often the transition was observed

Transition probability

Conditional probability of taking that transition from its source

For example, if 80 out of 100 journeys leaving product go to cart:

P(cart | product) = 0.80

The dashboard renders the graph interactively with React Flow.

🧠 How the behavioral analysis works

The behavioral analysis pipeline is deliberately transparent and explainable.

Step 1 — Raw events become BI events

The API reads the JSONL event stream and maps each raw event into the Behavioral Intelligence layer's Event model.

session_id → user_id
page       → screen
event      → event_type
action     → action
feature    → feature
properties → metadata

This creates a consistent internal representation for the analysis pipeline.

Step 2 — Events become user journeys

Events belonging to the same session are grouped and ordered into a journey.

Example:

[home, product, cart, checkout, confirmation]

A different session might look like:

[home, product]

Or:

[home, product, cart, product]

That last journey is particularly useful because it reveals backtracking behavior.

Step 3 — Journeys become a transition graph

The analysis layer counts consecutive transitions:

home → product
product → cart
cart → checkout
checkout → confirmation

For each source node, transition probabilities are derived from the observed outgoing counts.

In other words, TRACR models:

P(next_screen | current_screen)

This creates a compact representation of how users move through the application.

🔬 What-If simulation

The What-If system lets a developer ask:

What happens to the modeled user behavior if I change this transition probability?

The observed event data is never modified.

Instead, TRACR:

Deep-copies the baseline transition matrix.

Applies the requested probability override.

Re-normalizes the affected source row.

Simulates synthetic journeys from the baseline model.

Simulates the same number of journeys from the modified model.

Uses the same random seed for reproducibility.

Compares the resulting behavior.

This makes repeated demo runs deterministic for the same inputs.

Example

Suppose the baseline contains:

product → cart = 80%
product → home = 20%

A developer can experiment with a different probability distribution without changing the observed runtime data.

TRACR then shows the resulting change in the modeled behavior.

🫧 Behavioral Instability

The Behavioral Instability view turns What-If deviations into a visual simulation.

Each changed transition becomes a behavior bubble.

The bubbles encode:

size → deviation magnitude

movement → dynamic simulation

collision → competing behavioral pressure

severity → low / medium / high deviation

bursting → high-severity simulated instability

Instead of forcing the developer to stare at raw transition IDs, bubbles use semantic labels such as:

Backtrack
Forward Flow
Behavior Shift
Checkout Shift
Completion Push
Routing Surge
Flow Drift

The underlying transition remains available inside the dashboard for technical inspection.

Deviation thresholds

LOW       < 0.10
MEDIUM    0.10 – 0.30
HIGH      > 0.30

The instability field represents simulated transition stress. It is not a claim that the real application will fail in exactly the same way.

🚨 Anomaly Status

TRACR includes an Anomaly Status surface in the developer dashboard.

The current demo exposes descriptive behavioral alerts for observed route backtracking and also surfaces deviations generated by an active What-If simulation.

The anomaly system remains modular so the dedicated BI anomaly-detection layer can be expanded without changing the dashboard contract.

This separation is intentional:

Observed behavior
        ≠
Simulated What-If stress
        ≠
Future statistical anomaly detection

They are related signals, but they should not be presented as if they were the same thing.

🔄 Developer workflow

TRACR is designed around a compact investigation loop:

Runtime events
      ↓
Behavioral graph
      ↓
Identify common / unusual flows
      ↓
Modify a transition
      ↓
Run reproducible simulation
      ↓
Compare baseline vs What-If
      ↓
Inspect behavioral instability

The dashboard keeps the primary investigation context together:

Behavioral Graph

Developer Controls

What-If Analysis

Anomaly Status

User Flows

Recent Events

Behavioral Instability

The Behavioral Instability view is presented as a carousel panel so developers can move from:

"What is happening?"

to:

"What happens if I change it?"

without leaving the dashboard.

📈 Measuring impact

For our controlled demo task:

Determine the main user journeys through the sample application and identify the most frequent journey.

We measured:

Manual investigation     2:21  (141 seconds)
TRACR-assisted           0:27   (27 seconds)

Measured reduction        81%

This measurement comes from our controlled demonstration of that specific user-flow investigation task. It is not presented as a universal improvement across all debugging or maintenance workflows.

🏗️ Architecture

┌──────────────────────────────┐
│        Sample Web App        │
│       HTML / CSS / JS        │
└──────────────┬───────────────┘
               │
               │ behavioral events
               ▼
┌──────────────────────────────┐
│         FastAPI API          │
│ /collect /events /graph ...  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          BI Bridge           │
│ raw events → BI Events       │
│ journeys → graph → probs     │
└──────────────┬───────────────┘
               │
        ┌──────┴───────────┐
        ▼                  ▼
┌──────────────────┐  ┌──────────────────────┐
│ What-If Engine   │  │ React/Vite Dashboard │
│ baseline vs      │  │ graph / flows /      │
│ modified model   │  │ alerts / instability │
└──────────────────┘  └──────────────────────┘

🧰 Tech stack

Layer

Technology

Frontend

React + Vite

Graph visualization

React Flow

Backend

FastAPI + Uvicorn

Behavioral analysis

Python

Simulation comparison

SciPy

Event storage

JSONL

Sample application

HTML / CSS / JavaScript

📁 Project structure

GitGud/
├── app/
│   ├── api/
│   │   ├── bi_bridge.py
│   │   ├── collector.py
│   │   ├── routes.py
│   │   ├── schema.py
│   │   └── whatif.py
│   │
│   ├── twin/
│   │   ├── behavior_model.py
│   │   ├── simulator.py
│   │   └── transitions.py
│   │
│   └── analysis/
│       ├── anomaly_detection.py
│       ├── feature_usage.py
│       └── user_flows.py
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── api/
│       └── styles/
│
├── sample_project/
│   ├── index.html
│   ├── style.css
│   ├── tracr.js
│   └── seed.js
│
├── docs/
│   └── screenshots/
│       ├── dashboard.png
│       └── instability.png
│
└── data/
    └── events.jsonl

▶️ Running the demo

1. Start the backend

cd GitGud
uvicorn app.main:app --reload

The API will be available at:

http://localhost:8000

2. Start the frontend

cd frontend
npm install
npm run dev

3. Generate sample events

cd sample_project
node seed.js

The seeded data creates multiple synthetic user-session patterns for the dashboard.

4. Serve the sample application

python -m http.server 3000

Then open the TRACR dashboard through the Vite development server.

Generate or inspect events in the sample application and refresh the dashboard.

🔌 API surface

Endpoint

Purpose

POST /collect

Persist a behavioral event

GET /events

Read recent events

GET /health

API health check

GET /graph

Return the behavioral graph

GET /flows

Return ranked user journeys

GET /anomalies

Return behavioral alerts

GET /summary

Return session/event summary

GET /whatif/baseline

Return baseline transition probabilities

POST /whatif/simulate

Run a reproducible What-If simulation

💡 Why TRACR?

TRACR is built around a simple idea:

Logs tell you what happened. Behavioral models help you understand how users moved through the system — and What-If simulation lets you explore how that behavior could change.

The result is a developer workflow that connects:

runtime observation → behavioral structure → controlled simulation → visual investigation

in one place.

🏆 Hackathon context

TRACR was created as a working prototype for the Digital IBM Bob 2.0 Hackathon.

The project focuses on the application-maintenance and debugging workflow described by the challenge: identify a concrete developer problem, build a working prototype around a real or sample project, and demonstrate measurable productivity or effort improvements.

TRACR applies that idea to a specific problem: understanding application behavior from the perspective of the users moving through the system.

👥 Team

TRACR was designed and developed by a two-person team.

Druv Ghimire

Development & Product

Responsible for the application architecture, API layer, frontend dashboard, runtime event collection, What-If integration, developer workflow, and overall product implementation.

Arhant Ved

Behavioral Intelligence

Responsible for the behavioral modeling layer, transition graph construction, user-journey analysis, simulation logic, and behavioral interpretation that powers TRACR's runtime intelligence.

Together, we built TRACR as an end-to-end prototype connecting runtime application behavior with an interactive developer investigation workflow.

🔗 IBM Bob 2.0

TRACR was built specifically for the IBM Bob 2.0 hackathon.

Relevant IBM resources:

IBM Bob 2.0 release

IBM Bob documentation

IBM Developer hackathons

<div align="center">

Built with curiosity, experimentation, and IBM Bob 2.0 ☕️

Druv Ghimire · Arhant Ved

Observe. Model. Simulate. Investigate.

</div>