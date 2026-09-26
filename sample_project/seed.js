#!/usr/bin/env node
/**
 * seed.js — TRACR demo data generator for the sample e-commerce app.
 *
 * Sends 30 pre-scripted sessions to POST http://localhost:8000/collect
 * so the TRACR dashboard shows a non-trivial behavioral graph immediately,
 * without any manual browser interaction.
 *
 * Usage:
 *   node sample_project/seed.js
 *   node sample_project/seed.js --api http://localhost:8000  (override base URL)
 *
 * Requirements:
 *   Node.js 18+ (uses built-in fetch — no npm install needed)
 *
 * Session distribution (30 total):
 *   15  happy path       home → product → cart → checkout → confirmation
 *    8  browse & abandon home → product → home
 *    5  cart dropout     home → product → cart → home
 *    2  deep link        product → cart → checkout → confirmation
 */

"use strict";

// ── Configuration ─────────────────────────────────────────────────────────────

var apiBase = "http://localhost:8000";
for (var i = 0; i < process.argv.length - 1; i++) {
  if (process.argv[i] === "--api") {
    apiBase = process.argv[i + 1];
  }
}
var COLLECT_URL = apiBase + "/collect";

// ── UUID generator (no crypto module import needed for Node 18+) ───────────────

function uuid() {
  // Use crypto.randomUUID if available (Node 18+), else fall back
  if (
    typeof globalThis.crypto !== "undefined" &&
    typeof globalThis.crypto.randomUUID === "function"
  ) {
    return globalThis.crypto.randomUUID();
  }
  // Fallback for older Node
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0;
    var v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ── Journey templates ──────────────────────────────────────────────────────────

/**
 * Each template is an array of { page, event, properties } steps.
 * Timestamps are generated as sequential ISO-8601 strings starting from baseTime,
 * with 5 seconds between each event.
 */
var TEMPLATES = {
  happy: [
    { page: "home",         event: "page_view",        properties: {} },
    { page: "product",      event: "page_view",        properties: {} },
    { page: "product",      event: "product_view",     properties: { product_id: "demo-001", product_name: "Demo Widget Pro" } },
    { page: "product",      event: "add_to_cart",      properties: { product_id: "demo-001", quantity: 1 } },
    { page: "cart",         event: "page_view",        properties: {} },
    { page: "cart",         event: "begin_checkout",   properties: { cart_value: 29.99 } },
    { page: "checkout",     event: "page_view",        properties: {} },
    { page: "checkout",     event: "purchase_complete",properties: { order_id: "ORD-SEED", total: 29.99 } },
    { page: "confirmation", event: "page_view",        properties: {} },
  ],
  abandon: [
    { page: "home",    event: "page_view",    properties: {} },
    { page: "product", event: "page_view",    properties: {} },
    { page: "product", event: "product_view", properties: { product_id: "demo-001" } },
    { page: "home",    event: "page_view",    properties: {} },
  ],
  dropout: [
    { page: "home",    event: "page_view",   properties: {} },
    { page: "product", event: "page_view",   properties: {} },
    { page: "product", event: "product_view",properties: { product_id: "demo-001" } },
    { page: "product", event: "add_to_cart", properties: { product_id: "demo-001", quantity: 1 } },
    { page: "cart",    event: "page_view",   properties: {} },
    { page: "home",    event: "page_view",   properties: {} },
  ],
  deeplink: [
    { page: "product",      event: "page_view",        properties: {} },
    { page: "product",      event: "product_view",     properties: { product_id: "demo-001" } },
    { page: "product",      event: "add_to_cart",      properties: { product_id: "demo-001", quantity: 1 } },
    { page: "cart",         event: "page_view",        properties: {} },
    { page: "cart",         event: "begin_checkout",   properties: { cart_value: 29.99 } },
    { page: "checkout",     event: "page_view",        properties: {} },
    { page: "checkout",     event: "purchase_complete",properties: { order_id: "ORD-SEED", total: 29.99 } },
    { page: "confirmation", event: "page_view",        properties: {} },
  ],
};

// Distribution: 15 happy, 8 abandon, 5 dropout, 2 deeplink = 30 total
var SESSION_PLAN = []
  .concat(Array(15).fill("happy"))
  .concat(Array(8).fill("abandon"))
  .concat(Array(5).fill("dropout"))
  .concat(Array(2).fill("deeplink"));

// ── Event builder ──────────────────────────────────────────────────────────────

/**
 * Build a list of EventPayload-compatible objects for one session.
 * baseTime is a Unix timestamp (ms); events are spaced 5 seconds apart.
 */
function buildSession(journeyKey, sessionId, baseTimeMs) {
  var steps = TEMPLATES[journeyKey];
  return steps.map(function (step, idx) {
    return {
      session_id: sessionId,
      timestamp: new Date(baseTimeMs + idx * 5000).toISOString(),
      page: step.page,
      event: step.event,
      properties: step.properties,
    };
  });
}

// ── HTTP post ──────────────────────────────────────────────────────────────────

async function postEvent(payload) {
  var response = await fetch(COLLECT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("HTTP " + response.status + " for event " + payload.event);
  }
}

// ── Main ───────────────────────────────────────────────────────────────────────

async function main() {
  console.log("TRACR seed script — sending " + SESSION_PLAN.length + " sessions to " + COLLECT_URL);
  console.log("");

  // Stagger session base times across the past hour so timestamps look realistic
  var now = Date.now();
  var totalSessions = SESSION_PLAN.length;
  var intervalMs = (60 * 60 * 1000) / totalSessions; // spread over 1 hour

  var totalEvents = 0;
  var failed = 0;

  for (var s = 0; s < totalSessions; s++) {
    var journeyKey = SESSION_PLAN[s];
    var sessionId  = uuid();
    var baseTimeMs = now - (totalSessions - s) * intervalMs;
    var events     = buildSession(journeyKey, sessionId, baseTimeMs);

    var ok = true;
    for (var e = 0; e < events.length; e++) {
      try {
        await postEvent(events[e]);
        totalEvents++;
      } catch (err) {
        console.error("  ERROR: " + err.message);
        ok = false;
        failed++;
        break;
      }
    }

    if (ok) {
      console.log(
        "  session " + (s + 1).toString().padStart(2, " ") + "/" + totalSessions +
        "  [" + journeyKey.padEnd(8) + "]" +
        "  " + events.length + " events" +
        "  id=" + sessionId.substring(0, 8) + "..."
      );
    }
  }

  console.log("");
  console.log("Done.");
  console.log("  Sessions sent : " + (totalSessions - failed) + "/" + totalSessions);
  console.log("  Events sent   : " + totalEvents);
  if (failed > 0) {
    console.log("  Failures      : " + failed);
    process.exit(1);
  }
}

main().catch(function (err) {
  console.error("Fatal error:", err.message);
  console.error("Is the TRACR API running?  uvicorn app.main:app --reload --port 8000");
  process.exit(1);
});
