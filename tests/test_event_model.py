"""
Unit tests for app/twin/behavior_model.py — Event model and journey builder.

Covers all tests specified in the plan's test_event_model.py section, plus
one test per source shape to verify all three normalise() mappings.
"""

import pytest

from app.twin.behavior_model import Event, normalise, build_journeys


# ---------------------------------------------------------------------------
# normalise() — "default" source (canonical field names)
# ---------------------------------------------------------------------------

class TestNormaliseDefault:
    def test_normalise_valid_event(self):
        raw = {
            "user_id": "u1",
            "timestamp": 1000.0,
            "event_type": "page_view",
            "screen": "home",
            "action": "view",
            "feature": "browse",
        }
        event = normalise(raw)
        assert isinstance(event, Event)
        assert event.user_id == "u1"
        assert event.timestamp == 1000.0
        assert event.event_type == "page_view"
        assert event.screen == "home"
        assert event.action == "view"
        assert event.feature == "browse"

    def test_normalise_metadata_defaults_to_empty(self):
        """When 'metadata' key is absent, Event.metadata must be an empty dict."""
        raw = {
            "user_id": "u1",
            "timestamp": 1000.0,
            "event_type": "click",
            "screen": "home",
            "action": "view",
            "feature": "browse",
        }
        event = normalise(raw)
        assert event.metadata == {}

    def test_normalise_metadata_preserved(self):
        raw = {
            "user_id": "u1",
            "timestamp": 1000.0,
            "event_type": "click",
            "screen": "home",
            "action": "view",
            "feature": "browse",
            "metadata": {"button": "nav"},
        }
        event = normalise(raw)
        assert event.metadata == {"button": "nav"}

    def test_normalise_missing_required_field(self):
        """Missing 'screen' must raise ValueError naming the field."""
        raw = {
            "user_id": "u1",
            "timestamp": 1000.0,
            "event_type": "click",
            # "screen" omitted
            "action": "view",
            "feature": "browse",
        }
        with pytest.raises(ValueError, match="screen"):
            normalise(raw)

    def test_normalise_empty_required_field_raises(self):
        """An empty string for a required field is treated as missing."""
        raw = {
            "user_id": "u1",
            "timestamp": 1000.0,
            "event_type": "click",
            "screen": "",
            "action": "view",
            "feature": "browse",
        }
        with pytest.raises(ValueError, match="screen"):
            normalise(raw)

    def test_normalise_unknown_source_raises(self):
        raw = {"user_id": "u1", "timestamp": 1.0, "event_type": "x",
               "screen": "x", "action": "x", "feature": "x"}
        with pytest.raises(ValueError, match="Unknown source"):
            normalise(raw, source="unknown_source")


# ---------------------------------------------------------------------------
# normalise() — "frontend" source shape
# ---------------------------------------------------------------------------

class TestNormaliseFrontend:
    def _raw(self, **overrides):
        base = {
            "userId": "u1",
            "ts": 1000.0,
            "type": "page_view",
            "page": "home",
            "action": "view",
            "feature": "browse",
        }
        base.update(overrides)
        return base

    def test_normalise_frontend_valid(self):
        event = normalise(self._raw(), source="frontend")
        assert event.user_id == "u1"
        assert event.timestamp == 1000.0
        assert event.event_type == "page_view"
        assert event.screen == "home"

    def test_normalise_frontend_meta_defaults_to_empty(self):
        event = normalise(self._raw(), source="frontend")
        assert event.metadata == {}

    def test_normalise_frontend_meta_preserved(self):
        event = normalise(self._raw(meta={"ab": "test_v1"}), source="frontend")
        assert event.metadata == {"ab": "test_v1"}

    def test_normalise_frontend_missing_page_raises(self):
        raw = {
            "userId": "u1",
            "ts": 1000.0,
            "type": "click",
            # "page" omitted → maps to "screen"
            "action": "view",
            "feature": "browse",
        }
        with pytest.raises(ValueError, match="screen"):
            normalise(raw, source="frontend")


# ---------------------------------------------------------------------------
# normalise() — "backend" source shape
# ---------------------------------------------------------------------------

class TestNormaliseBackend:
    def _raw(self, **overrides):
        base = {
            "uid": "u1",
            "time": 1000.0,
            "kind": "api_call",
            "route": "home",
            "op": "view",
            "area": "browse",
        }
        base.update(overrides)
        return base

    def test_normalise_backend_valid(self):
        event = normalise(self._raw(), source="backend")
        assert event.user_id == "u1"
        assert event.timestamp == 1000.0
        assert event.event_type == "api_call"
        assert event.screen == "home"
        assert event.action == "view"
        assert event.feature == "browse"

    def test_normalise_backend_extra_defaults_to_empty(self):
        event = normalise(self._raw(), source="backend")
        assert event.metadata == {}

    def test_normalise_backend_extra_preserved(self):
        event = normalise(self._raw(extra={"status": 200}), source="backend")
        assert event.metadata == {"status": 200}

    def test_normalise_backend_missing_uid_raises(self):
        raw = {
            # "uid" omitted → maps to "user_id"
            "time": 1000.0,
            "kind": "click",
            "route": "home",
            "op": "view",
            "area": "browse",
        }
        with pytest.raises(ValueError, match="user_id"):
            normalise(raw, source="backend")


# ---------------------------------------------------------------------------
# build_journeys()
# ---------------------------------------------------------------------------

class TestBuildJourneys:
    def _make_event(self, user_id, timestamp, screen="home"):
        return Event(
            user_id=user_id,
            timestamp=timestamp,
            event_type="page_view",
            screen=screen,
            action="view",
            feature="browse",
        )

    def test_build_journeys_groups_by_user(self):
        """Two users → two journey keys."""
        events = [
            self._make_event("u1", 1000.0),
            self._make_event("u2", 2000.0),
            self._make_event("u1", 1005.0),
        ]
        journeys = build_journeys(events)
        assert set(journeys.keys()) == {"u1", "u2"}
        assert len(journeys["u1"]) == 2
        assert len(journeys["u2"]) == 1

    def test_build_journeys_sorted_by_timestamp(self):
        """Out-of-order events must be sorted ascending by timestamp."""
        events = [
            self._make_event("u1", 1020.0, screen="cart"),
            self._make_event("u1", 1000.0, screen="home"),
            self._make_event("u1", 1005.0, screen="product"),
        ]
        journeys = build_journeys(events)
        screens = [e.screen for e in journeys["u1"]]
        assert screens == ["home", "product", "cart"]

    def test_build_journeys_empty_input(self):
        assert build_journeys([]) == {}

    def test_build_journeys_single_event(self):
        events = [self._make_event("u1", 1000.0)]
        journeys = build_journeys(events)
        assert len(journeys["u1"]) == 1

    def test_build_journeys_returns_event_objects(self):
        """Each journey value must contain Event instances."""
        events = [self._make_event("u1", 1000.0)]
        journeys = build_journeys(events)
        assert all(isinstance(e, Event) for e in journeys["u1"])

    def test_build_journeys_does_not_mutate_input(self):
        """The original list must not be reordered."""
        events = [
            self._make_event("u1", 1020.0),
            self._make_event("u1", 1000.0),
        ]
        original_order = [e.timestamp for e in events]
        build_journeys(events)
        assert [e.timestamp for e in events] == original_order
