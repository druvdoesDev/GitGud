/**
 * tracr.js — TRACR instrumentation snippet for the sample e-commerce app.
 *
 * Usage:
 *   <script src="tracr.js"></script>
 *
 * Public API (window.tracr):
 *   track(page, event, properties)          — fire a single event
 *   simulateJourney(steps, delayMs)         — replay a scripted journey
 *
 * Automatic behaviour:
 *   - Generates a session_id (UUID) stored in sessionStorage on first load.
 *   - Fires a "page_view" event on every hashchange.
 *   - Fires a "page_view" event for the initial hash on page load.
 *   - All network errors are silenced — a failed POST never disrupts the app.
 *
 * Configuration:
 *   Change TRACR_API_BASE to point at a different API host/port if needed.
 */

(function () {
  "use strict";

  // ── Configuration ──────────────────────────────────────────────────────────
  var TRACR_API_BASE = "http://localhost:8000";
  var SESSION_KEY = "tracr_session_id";

  // ── Session management ─────────────────────────────────────────────────────

  /**
   * Generate a v4-style UUID using the Web Crypto API.
   * Falls back to a Math.random-based approach for environments that lack it.
   */
  function generateUUID() {
    if (
      typeof crypto !== "undefined" &&
      typeof crypto.randomUUID === "function"
    ) {
      return crypto.randomUUID();
    }
    // Fallback: RFC4122 v4 UUID via Math.random
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        var r = (Math.random() * 16) | 0;
        var v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      }
    );
  }

  /**
   * Return the current session_id from sessionStorage.
   * Creates and stores a fresh UUID if none exists yet.
   */
  function getSessionId() {
    var id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = generateUUID();
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  }

  /**
   * Overwrite sessionStorage with a brand-new session_id and return it.
   * Called at the start of each simulated journey so every simulation
   * is counted as a distinct session by the BI layer.
   */
  function newSessionId() {
    var id = generateUUID();
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  }

  // ── Event posting ──────────────────────────────────────────────────────────

  /**
   * POST a single event to /collect.
   * Fire-and-forget: the promise is never awaited and errors are silenced.
   *
   * @param {string} sessionId  - UUID identifying the current session
   * @param {string} page       - logical page name ("home", "product", …)
   * @param {string} event      - event type ("page_view", "add_to_cart", …)
   * @param {Object} properties - optional free-form metadata
   */
  function post(sessionId, page, event, properties) {
    try {
      fetch(TRACR_API_BASE + "/collect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          timestamp: new Date().toISOString(),
          page: page,
          event: event,
          properties: properties || {},
        }),
      }).catch(function () {
        /* silenced */
      });
    } catch (_) {
      /* silenced — fetch itself may throw in very old environments */
    }
  }

  // ── Hash → page name ───────────────────────────────────────────────────────

  /** Map window.location.hash to a canonical page name. */
  function hashToPage(hash) {
    var map = {
      "#home": "home",
      "#product": "product",
      "#cart": "cart",
      "#checkout": "checkout",
      "#confirmation": "confirmation",
    };
    return map[hash] || hash.replace(/^#/, "") || "home";
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Fire a single event using the current session.
   *
   * @param {string} page
   * @param {string} event
   * @param {Object} [properties]
   */
  function track(page, event, properties) {
    post(getSessionId(), page, event, properties || {});
  }

  /**
   * Replay a scripted journey as a series of timed steps.
   *
   * A fresh session_id is created at the start so each simulation counts
   * as a completely separate session in the behavioral analysis.
   *
   * Each step is an object:
   *   { hash: "#product", event: "product_view", properties: {...} }
   *
   * The hash navigation happens first, which also triggers the hashchange
   * listener (firing page_view). The extra event in the step (if provided)
   * fires immediately after.
   *
   * @param {Array<{hash: string, event?: string, properties?: Object}>} steps
   * @param {number} [delayMs=300]  Pause between steps in milliseconds
   */
  function simulateJourney(steps, delayMs) {
    var delay = typeof delayMs === "number" ? delayMs : 300;
    // Create a fresh session for this simulation run
    var simSessionId = newSessionId();
    var index = 0;

    function runStep() {
      if (index >= steps.length) return;
      var step = steps[index];
      index++;

      // Navigate — this triggers hashchange → page_view auto-fires
      window.location.hash = step.hash;

      // Fire the extra event for this step (if any) after a short pause
      // so it lands after the auto page_view
      if (step.event) {
        setTimeout(function () {
          post(simSessionId, hashToPage(step.hash), step.event, step.properties || {});
        }, 50);
      }

      setTimeout(runStep, delay);
    }

    runStep();
  }

  // ── Automatic page_view tracking ───────────────────────────────────────────

  window.addEventListener("hashchange", function () {
    var page = hashToPage(window.location.hash);
    post(getSessionId(), page, "page_view", {});
  });

  // Fire for the initial page on load
  window.addEventListener("load", function () {
    var hash = window.location.hash || "#home";
    if (!window.location.hash) {
      window.location.hash = "#home";
    }
    var page = hashToPage(hash);
    post(getSessionId(), page, "page_view", {});
  });

  // ── Expose public API ──────────────────────────────────────────────────────
  window.tracr = {
    track: track,
    simulateJourney: simulateJourney,
  };
})();
