/**
 * TRACR API client.
 *
 * One function per endpoint. All functions return parsed JSON or throw.
 * The caller (App.jsx) is responsible for error handling.
 *
 * Change API_BASE to point at a different host/port if needed.
 */

const API_BASE = "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`);
  return res.json();
}

export const fetchHealth    = () => get("/health");
export const fetchGraph     = () => get("/graph");
export const fetchFlows     = () => get("/flows");
export const fetchAnomalies = () => get("/anomalies");
export const fetchSummary   = () => get("/summary");
export const fetchEvents    = () => get("/events");
