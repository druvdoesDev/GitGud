import { useState, useCallback } from "react";
import { useAutoRefresh } from "./hooks/useAutoRefresh.js";
import {
  fetchHealth,
  fetchGraph,
  fetchFlows,
  fetchAnomalies,
  fetchSummary,
  fetchEvents,
} from "./api/client.js";

import StatusBar    from "./components/StatusBar.jsx";
import SummaryBar   from "./components/SummaryBar.jsx";
import GraphView    from "./components/GraphView.jsx";
import FlowTable    from "./components/FlowTable.jsx";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import EventFeed    from "./components/EventFeed.jsx";

const REFRESH_INTERVAL = 5000; // ms

export default function App() {
  // null = not yet loaded; object = loaded data
  const [graph,     setGraph]     = useState(null);
  const [flows,     setFlows]     = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [summary,   setSummary]   = useState(null);
  const [events,    setEvents]    = useState(null);

  // "loading" | "ok" | "error"
  const [apiStatus, setApiStatus] = useState("loading");
  const [apiError,  setApiError]  = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      // Health check first — cheap, fast, surfaces API-down state clearly
      await fetchHealth();

      const [graphData, flowsData, anomaliesData, summaryData, eventsData] =
        await Promise.all([
          fetchGraph(),
          fetchFlows(),
          fetchAnomalies(),
          fetchSummary(),
          fetchEvents(),
        ]);

      setGraph(graphData);
      setFlows(flowsData.flows);
      setAnomalies(anomaliesData.anomalies);
      setSummary(summaryData);
      setEvents(eventsData.events);
      setApiStatus("ok");
      setApiError(null);
    } catch (err) {
      setApiStatus("error");
      setApiError(err.message ?? "Could not reach the TRACR API.");
    }
  }, []);

  const refresh = useAutoRefresh(fetchAll, REFRESH_INTERVAL);

  return (
    <>
      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header className="topbar">
        <span className="topbar-brand">
          TRAC<span>R</span>
        </span>
        <StatusBar status={apiStatus} />
        <div className="topbar-spacer" />
        <button
          className="btn-refresh"
          onClick={refresh}
          disabled={apiStatus === "loading"}
        >
          ↻ Refresh
        </button>
      </header>

      {/* ── Summary strip ───────────────────────────────────────────────── */}
      <SummaryBar summary={summary} />

      {/* ── API error banner ────────────────────────────────────────────── */}
      {apiStatus === "error" && apiError && (
        <div className="error-banner">
          <strong>API Unavailable</strong> — {apiError}.{" "}
          Is <code>uvicorn app.main:app</code> running on port 8000?
        </div>
      )}

      {/* ── Main dashboard grid ─────────────────────────────────────────── */}
      <div className="dashboard">

        {/* Left column — Behavioral graph */}
        <div className="panel panel-graph">
          <div className="panel-header">
            <span className="panel-title">Behavioral Graph</span>
            {graph && (
              <span className="panel-count">
                {graph.nodes.length} nodes · {graph.edges.length} edges
              </span>
            )}
          </div>
          <div className="panel-body" style={{ padding: 0, flex: 1 }}>
            <GraphView graph={graph} />
          </div>
        </div>

        {/* Right column top — User flows */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Top User Flows</span>
            {flows && (
              <span className="panel-count">{flows.length} paths</span>
            )}
          </div>
          <div className="panel-body">
            <FlowTable flows={flows} />
          </div>
        </div>

        {/* Right column middle — Anomalies */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Anomalies</span>
            {anomalies && anomalies.length > 0 && (
              <span className="panel-count">{anomalies.length} detected</span>
            )}
          </div>
          <div className="panel-body">
            <AnomalyPanel anomalies={anomalies} />
          </div>
        </div>

        {/* Right column bottom — Event feed */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Recent Events</span>
            {events && (
              <span className="panel-count">last {Math.min(events.length, 20)} of {events.length}</span>
            )}
          </div>
          <div className="panel-body" style={{ padding: "0 1rem" }}>
            <EventFeed events={events} />
          </div>
        </div>

      </div>
    </>
  );
}
