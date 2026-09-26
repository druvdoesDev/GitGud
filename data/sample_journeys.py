"""
TRACR sample journey fixtures.

Three journeys are provided in multiple forms:

1.  RAW_DEFAULT   — dicts already in canonical (default) field names.
2.  RAW_FRONTEND  — same events expressed as frontend beacon payloads.
3.  RAW_BACKEND   — same events expressed as backend log payloads.
4.  EVENTS_*      — pre-built Event objects (used by graph/simulation tests).

Journey descriptions
--------------------
Journey 1 (u1) — normal checkout flow (5 events)
Journey 2 (u2) — browse without purchase (4 events)
Journey 3 (u3) — repeat of journey 1 with timestamps offset by 3000 (5 events)

These journeys produce the following expected transition counts when keyed by
"screen" (see plan section "Expected Behavioral Graph / Probability Output"):

  home → product   : 3   P = 0.75
  home → search    : 1   P = 0.25
  product → cart   : 2   P = 0.667
  product → home   : 1   P = 0.333
  cart → checkout  : 2   P = 1.0
  checkout→confirm : 2   P = 1.0
  search → product : 1   P = 1.0
"""

from app.twin.behavior_model import Event

# ---------------------------------------------------------------------------
# Raw dicts — "default" source shape (canonical field names)
# ---------------------------------------------------------------------------

RAW_DEFAULT: list[dict] = [
    # Journey 1 — u1 checkout
    {"user_id": "u1", "timestamp": 1000.0, "event_type": "page_view", "screen": "home",     "action": "view",          "feature": "browse"},
    {"user_id": "u1", "timestamp": 1005.0, "event_type": "click",     "screen": "product",  "action": "view_product",  "feature": "browse"},
    {"user_id": "u1", "timestamp": 1020.0, "event_type": "click",     "screen": "cart",     "action": "add_to_cart",   "feature": "checkout"},
    {"user_id": "u1", "timestamp": 1040.0, "event_type": "page_view", "screen": "checkout", "action": "view",          "feature": "checkout"},
    {"user_id": "u1", "timestamp": 1060.0, "event_type": "click",     "screen": "confirm",  "action": "submit_order",  "feature": "checkout"},
    # Journey 2 — u2 browse
    {"user_id": "u2", "timestamp": 2000.0, "event_type": "page_view", "screen": "home",    "action": "view",          "feature": "browse"},
    {"user_id": "u2", "timestamp": 2010.0, "event_type": "click",     "screen": "search",  "action": "search",        "feature": "search"},
    {"user_id": "u2", "timestamp": 2025.0, "event_type": "click",     "screen": "product", "action": "view_product",  "feature": "browse"},
    {"user_id": "u2", "timestamp": 2040.0, "event_type": "page_view", "screen": "home",    "action": "view",          "feature": "browse"},
    # Journey 3 — u3 repeat of journey 1 (timestamps +3000)
    {"user_id": "u3", "timestamp": 4000.0, "event_type": "page_view", "screen": "home",     "action": "view",          "feature": "browse"},
    {"user_id": "u3", "timestamp": 4005.0, "event_type": "click",     "screen": "product",  "action": "view_product",  "feature": "browse"},
    {"user_id": "u3", "timestamp": 4020.0, "event_type": "click",     "screen": "cart",     "action": "add_to_cart",   "feature": "checkout"},
    {"user_id": "u3", "timestamp": 4040.0, "event_type": "page_view", "screen": "checkout", "action": "view",          "feature": "checkout"},
    {"user_id": "u3", "timestamp": 4060.0, "event_type": "click",     "screen": "confirm",  "action": "submit_order",  "feature": "checkout"},
]

# ---------------------------------------------------------------------------
# Raw dicts — "frontend" source shape
# ---------------------------------------------------------------------------

RAW_FRONTEND: list[dict] = [
    # Journey 1 — u1 checkout
    {"userId": "u1", "ts": 1000.0, "type": "page_view", "page": "home",     "action": "view",          "feature": "browse"},
    {"userId": "u1", "ts": 1005.0, "type": "click",     "page": "product",  "action": "view_product",  "feature": "browse"},
    {"userId": "u1", "ts": 1020.0, "type": "click",     "page": "cart",     "action": "add_to_cart",   "feature": "checkout"},
    {"userId": "u1", "ts": 1040.0, "type": "page_view", "page": "checkout", "action": "view",          "feature": "checkout"},
    {"userId": "u1", "ts": 1060.0, "type": "click",     "page": "confirm",  "action": "submit_order",  "feature": "checkout"},
    # Journey 2 — u2 browse
    {"userId": "u2", "ts": 2000.0, "type": "page_view", "page": "home",    "action": "view",          "feature": "browse"},
    {"userId": "u2", "ts": 2010.0, "type": "click",     "page": "search",  "action": "search",        "feature": "search"},
    {"userId": "u2", "ts": 2025.0, "type": "click",     "page": "product", "action": "view_product",  "feature": "browse"},
    {"userId": "u2", "ts": 2040.0, "type": "page_view", "page": "home",    "action": "view",          "feature": "browse"},
    # Journey 3 — u3
    {"userId": "u3", "ts": 4000.0, "type": "page_view", "page": "home",     "action": "view",          "feature": "browse"},
    {"userId": "u3", "ts": 4005.0, "type": "click",     "page": "product",  "action": "view_product",  "feature": "browse"},
    {"userId": "u3", "ts": 4020.0, "type": "click",     "page": "cart",     "action": "add_to_cart",   "feature": "checkout"},
    {"userId": "u3", "ts": 4040.0, "type": "page_view", "page": "checkout", "action": "view",          "feature": "checkout"},
    {"userId": "u3", "ts": 4060.0, "type": "click",     "page": "confirm",  "action": "submit_order",  "feature": "checkout"},
]

# ---------------------------------------------------------------------------
# Raw dicts — "backend" source shape
# ---------------------------------------------------------------------------

RAW_BACKEND: list[dict] = [
    # Journey 1 — u1 checkout
    {"uid": "u1", "time": 1000.0, "kind": "page_view", "route": "home",     "op": "view",          "area": "browse"},
    {"uid": "u1", "time": 1005.0, "kind": "click",     "route": "product",  "op": "view_product",  "area": "browse"},
    {"uid": "u1", "time": 1020.0, "kind": "click",     "route": "cart",     "op": "add_to_cart",   "area": "checkout"},
    {"uid": "u1", "time": 1040.0, "kind": "page_view", "route": "checkout", "op": "view",          "area": "checkout"},
    {"uid": "u1", "time": 1060.0, "kind": "click",     "route": "confirm",  "op": "submit_order",  "area": "checkout"},
    # Journey 2 — u2 browse
    {"uid": "u2", "time": 2000.0, "kind": "page_view", "route": "home",    "op": "view",          "area": "browse"},
    {"uid": "u2", "time": 2010.0, "kind": "click",     "route": "search",  "op": "search",        "area": "search"},
    {"uid": "u2", "time": 2025.0, "kind": "click",     "route": "product", "op": "view_product",  "area": "browse"},
    {"uid": "u2", "time": 2040.0, "kind": "page_view", "route": "home",    "op": "view",          "area": "browse"},
    # Journey 3 — u3
    {"uid": "u3", "time": 4000.0, "kind": "page_view", "route": "home",     "op": "view",          "area": "browse"},
    {"uid": "u3", "time": 4005.0, "kind": "click",     "route": "product",  "op": "view_product",  "area": "browse"},
    {"uid": "u3", "time": 4020.0, "kind": "click",     "route": "cart",     "op": "add_to_cart",   "area": "checkout"},
    {"uid": "u3", "time": 4040.0, "kind": "page_view", "route": "checkout", "op": "view",          "area": "checkout"},
    {"uid": "u3", "time": 4060.0, "kind": "click",     "route": "confirm",  "op": "submit_order",  "area": "checkout"},
]

# ---------------------------------------------------------------------------
# Pre-built Event objects — used directly by graph and simulation tests
# ---------------------------------------------------------------------------

# Journey 1: u1 checkout flow
EVENTS_U1: list[Event] = [
    Event("u1", 1000.0, "page_view", "home",     "view",         "browse"),
    Event("u1", 1005.0, "click",     "product",  "view_product", "browse"),
    Event("u1", 1020.0, "click",     "cart",     "add_to_cart",  "checkout"),
    Event("u1", 1040.0, "page_view", "checkout", "view",         "checkout"),
    Event("u1", 1060.0, "click",     "confirm",  "submit_order", "checkout"),
]

# Journey 2: u2 browse without purchase
EVENTS_U2: list[Event] = [
    Event("u2", 2000.0, "page_view", "home",    "view",         "browse"),
    Event("u2", 2010.0, "click",     "search",  "search",       "search"),
    Event("u2", 2025.0, "click",     "product", "view_product", "browse"),
    Event("u2", 2040.0, "page_view", "home",    "view",         "browse"),
]

# Journey 3: u3 repeat of journey 1
EVENTS_U3: list[Event] = [
    Event("u3", 4000.0, "page_view", "home",     "view",         "browse"),
    Event("u3", 4005.0, "click",     "product",  "view_product", "browse"),
    Event("u3", 4020.0, "click",     "cart",     "add_to_cart",  "checkout"),
    Event("u3", 4040.0, "page_view", "checkout", "view",         "checkout"),
    Event("u3", 4060.0, "click",     "confirm",  "submit_order", "checkout"),
]

# All events flat (mixed users) — used to test build_journeys grouping
ALL_EVENTS: list[Event] = EVENTS_U1 + EVENTS_U2 + EVENTS_U3

# All journeys as list-of-lists — used by graph builder and simulator
ALL_JOURNEYS: list[list[Event]] = [EVENTS_U1, EVENTS_U2, EVENTS_U3]
