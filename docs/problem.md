# The Problem TRACR Addresses

## Developer Investigation Today

When a developer is called to investigate a production issue or maintain an
unfamiliar application, they typically need to answer questions like:

- Which pages do users actually visit, and in what order?
- How frequently do users complete the intended flow vs. take an unexpected path?
- Where in the application do most sessions end?

Answering these questions today usually means cross-referencing multiple sources:

| Source | What it shows | What it doesn't show |
|--------|--------------|----------------------|
| Server logs | Individual requests, errors, latency | The user's journey across multiple requests |
| Application code | What the app *can* do | What users *actually* do |
| Analytics dashboards | Aggregate page views, funnels | Per-session behavioral sequences |
| User reports / support tickets | Symptoms | Frequency or reproducibility |

Each source uses a different vocabulary and requires a different skill to read.
Reconstructing a complete picture of user behavior requires switching between
tools, correlating timestamps, and building a mental model manually.

## What Is Missing

No single artifact shows how users move through an application as a structured,
navigable sequence — one that is:

- expressed in the developer's terms (pages, events, transitions)
- derived from real observed behavior rather than code paths
- explorable at a session level and aggregable across many sessions
- available without sending data to a third-party analytics platform

## The Cost

The manual investigation process has measurable properties. Some of these are
suitable for before/after comparison:

- **Number of sources** that must be consulted to reconstruct a single user journey
- **Number of files or queries** needed to understand which flows are common
- **Time to identify** which behavioral pattern is relevant to the issue at hand
- **Rework or misdirection** caused by investigating a flow that turned out to be rare

These are the quantities TRACR is designed to reduce. They are stated here as
observable and measurable, not as resolved claims.

## The TRACR Approach

TRACR captures behavioral events from an instrumented application and translates
them into a structured, developer-oriented map of observed user behavior:

- **Nodes** represent pages or screens users visited
- **Edges** represent observed transitions between pages
- **Probabilities** on each edge show how frequently users took that path
- **Flows** rank the most common complete journeys by session frequency

This map is derived from actual runtime behavior, not from code analysis. It is
updated each time new events are collected and is available through a local API
that requires no external services or authentication.

## What TRACR Does Not Claim

The current MVP does not include:

- **Anomaly detection** — the analysis module is designed but not yet
  implemented. The `/anomalies` endpoint exists and returns an empty list.
- **Feature usage analysis** — designed for a future milestone.
- **Automatic diagnosis** — TRACR surfaces behavioral evidence; it does not
  identify root causes automatically.
- **Production deployment** — the current implementation is localhost-only with
  no authentication or scaling.
