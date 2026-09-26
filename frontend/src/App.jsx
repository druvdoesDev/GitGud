import { useState, useCallback, useEffect } from "react";
import { useAutoRefresh } from "./hooks/useAutoRefresh.js";

import {
  fetchHealth,
  fetchGraph,
  fetchFlows,
  fetchAnomalies,
  fetchSummary,
  fetchEvents,
  fetchWhatifBaseline,
} from "./api/client.js";

import StatusBar from "./components/StatusBar.jsx";
import SummaryBar from "./components/SummaryBar.jsx";
import GraphView from "./components/GraphView.jsx";
import FlowTable from "./components/FlowTable.jsx";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import WhatIfPanel from "./components/WhatIfPanel.jsx";
import InstabilityView from "./components/InstabilityView.jsx";
import EventFeed from "./components/EventFeed.jsx";

const REFRESH_INTERVAL = 5000;

export default function App() {
  const [graph, setGraph] = useState(null);
  const [flows, setFlows] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState(null);
  const [baseline, setBaseline] = useState(null);

  const [whatifDeviations, setWhatifDeviations] = useState(null);
  const [whatifProbabilities, setWhatifProbabilities] = useState(null);

  const [apiStatus, setApiStatus] = useState("loading");
  const [apiError, setApiError] = useState(null);

  const [page, setPage] = useState(0);

  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("tracr-theme");
    return saved === "light" ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("tracr-theme", theme);
  }, [theme]);

  const fetchAll = useCallback(async () => {
    try {
      await fetchHealth();

      const [
        graphData,
        flowsData,
        anomaliesData,
        summaryData,
        eventsData,
        baselineData,
      ] = await Promise.all([
        fetchGraph(),
        fetchFlows(),
        fetchAnomalies(),
        fetchSummary(),
        fetchEvents(),
        fetchWhatifBaseline(),
      ]);

      setGraph(graphData);
      setFlows(flowsData.flows);

      // Backend returns:
      // { anomalies: [...] }
      setAnomalies(anomaliesData.anomalies ?? []);

      setSummary(summaryData);
      setEvents(eventsData.events);
      setBaseline(baselineData);

      setApiStatus("ok");
      setApiError(null);
    } catch (err) {
      setApiStatus("error");
      setApiError(
        err.message ?? "Could not reach the TRACR API."
      );
    }
  }, []);

  const refresh = useAutoRefresh(
    fetchAll,
    REFRESH_INTERVAL
  );

  // ==============================================================
  // WHAT-IF RESULT
  // ==============================================================

  const handleWhatIfResult = useCallback((result) => {
    setWhatifDeviations(
      result?.deviations ?? null
    );

    setWhatifProbabilities(
      result?.whatif_probabilities ?? null
    );
  }, []);

  // ==============================================================
  // COMBINED ANOMALY VIEW
  // ==============================================================

  const displayedAnomalies = [
    ...(anomalies ?? []),

    ...(whatifDeviations ?? []).map(
      (deviation) => ({
        type: "What-If deviation",

        description:
          `${deviation.from} → ${deviation.to} changed by ` +
          `${deviation.absolute_delta >= 0 ? "+" : ""}` +
          `${(
            deviation.absolute_delta * 100
          ).toFixed(1)}% under the active simulation.`,

        severity: deviation.severity,
      })
    ),
  ];

  const totalDisplayedAnomalies =
    displayedAnomalies.length;

  // ==============================================================
  // CAROUSEL
  // ==============================================================

  const goToInstability = useCallback(() => {
    setPage(1);
  }, []);

  const goToOverview = useCallback(() => {
    setPage(0);
  }, []);

  return (
    <div className="tracr-app">
      {/* ============================================================
          TOP BAR
          ============================================================ */}

      <header className="topbar">
        <span className="topbar-brand">
          TRAC<span>R</span>
        </span>

        <StatusBar status={apiStatus} />

        <div className="topbar-spacer" />

        <button
          className="theme-toggle"
          onClick={() =>
            setTheme((current) =>
              current === "dark"
                ? "light"
                : "dark"
            )
          }
          title={`Switch to ${
            theme === "dark"
              ? "light"
              : "dark"
          } mode`}
        >
          {theme === "dark"
            ? "☀ Light"
            : "◐ Dark"}
        </button>

        <button
          className="btn-refresh"
          onClick={refresh}
          disabled={
            apiStatus === "loading"
          }
        >
          ↻ Refresh
        </button>
      </header>

      {/* ============================================================
          SUMMARY
          ============================================================ */}

      <SummaryBar summary={summary} />

      {/* ============================================================
          ERROR
          ============================================================ */}

      {apiStatus === "error" &&
        apiError && (
          <div className="error-banner">
            <strong>
              API Unavailable
            </strong>{" "}
            — {apiError}. Is{" "}
            <code>
              uvicorn app.main:app
            </code>{" "}
            running on port 8000?
          </div>
        )}

      {/* ============================================================
          CAROUSEL
          ============================================================ */}

      <main className="carousel-frame">
        <div
          className={`carousel-track ${
            page === 1
              ? "show-instability"
              : ""
          }`}
        >
          {/* ========================================================
              PAGE 1 — INVESTIGATION OVERVIEW
              ======================================================== */}

          <section className="carousel-page overview-page">
            <div className="overview-grid">
              {/* ======================================================
                  MAIN GRAPH
                  ====================================================== */}

              <section className="panel panel-graph">
                <div className="panel-header">
                  <div>
                    <div className="panel-title">
                      Behavioral Graph
                    </div>

                    <div className="panel-subtitle">
                      Observed navigation
                      structure
                    </div>
                  </div>

                  {graph && (
                    <span className="panel-count">
                      {graph.nodes.length}{" "}
                      nodes ·{" "}
                      {graph.edges.length}{" "}
                      edges
                    </span>
                  )}
                </div>

                <div className="panel-body graph-panel-body">
                  <GraphView
                    graph={graph}
                    whatIfProbabilities={
                      whatifProbabilities
                    }
                  />
                </div>
              </section>

              {/* ======================================================
                  RIGHT SIDE
                  ====================================================== */}

              <aside className="overview-side">
                {/* ====================================================
                    DEVELOPER CONTROLS
                    ==================================================== */}

                <section className="panel control-panel">
                  <div className="panel-header">
                    <div>
                      <div className="panel-title">
                        Developer Controls
                      </div>

                      <div className="panel-subtitle">
                        Investigation
                        workspace
                      </div>
                    </div>
                  </div>

                  <div className="control-panel-body">
                    <div className="control-card">
                      <div className="control-card-label">
                        Graph interaction
                      </div>

                      <div className="control-card-text">
                        Drag nodes to inspect
                        paths. Use Fit to
                        recenter the
                        behavioral graph.
                      </div>
                    </div>

                    <div className="control-card">
                      <div className="control-card-label">
                        Live data
                      </div>

                      <div className="control-status-row">
                        <span
                          className={`control-status-dot ${
                            apiStatus === "ok"
                              ? "is-ok"
                              : apiStatus ===
                                "error"
                              ? "is-error"
                              : "is-loading"
                          }`}
                        />

                        <span>
                          {apiStatus ===
                          "ok"
                            ? "API connected"
                            : apiStatus ===
                              "error"
                            ? "API unavailable"
                            : "Connecting…"}
                        </span>
                      </div>
                    </div>
                  </div>
                </section>

                {/* ====================================================
                    WHAT-IF + CAROUSEL
                    ==================================================== */}

                <section className="panel panel-whatif">
                  <div className="panel-header">
                    <div>
                      <div className="panel-title">
                        What-If Analysis
                      </div>

                      <div className="panel-subtitle">
                        Stress-test transition
                        probabilities
                      </div>
                    </div>

                    {whatifDeviations?.length >
                      0 && (
                      <span className="panel-count">
                        {
                          whatifDeviations.length
                        }{" "}
                        deviations
                      </span>
                    )}
                  </div>

                  <div className="panel-body whatif-with-carousel">
                    <div className="whatif-content">
                      <WhatIfPanel
                        baseline={baseline}
                        onResult={
                          handleWhatIfResult
                        }
                      />
                    </div>

                    <div className="carousel-rail">
                      <button
                        className="carousel-next"
                        onClick={
                          goToInstability
                        }
                        title="Open behavioral instability"
                        aria-label="Open behavioral instability"
                      >
                        <span className="carousel-arrow">
                          ›
                        </span>
                      </button>

                      <div className="carousel-rail-label">
                        <span>
                          BEHAVIORAL
                        </span>

                        <strong>
                          INSTABILITY
                        </strong>
                      </div>
                    </div>
                  </div>
                </section>
              </aside>
            </div>

            {/* ========================================================
                COLLAPSED INFORMATION DRAWERS
                ======================================================== */}

            <div className="overview-drawers">
              {/* ======================================================
                  USER FLOWS
                  ====================================================== */}

              <details className="compact-dropdown">
                <summary>
                  <span>
                    Top User Flows
                  </span>

                  <small>
                    {flows
                      ? `${flows.length} paths`
                      : "loading"}
                  </small>
                </summary>

                <div className="compact-dropdown-body">
                  <FlowTable
                    flows={flows}
                  />
                </div>
              </details>

              {/* ======================================================
                  ANOMALY STATUS
                  ====================================================== */}

              <details className="compact-dropdown">
                <summary>
                  <span>
                    Anomaly Status
                  </span>

                  <small>
                    {anomalies === null
                      ? "loading"
                      : totalDisplayedAnomalies ===
                        0
                      ? "clear"
                      : `${totalDisplayedAnomalies} found`}
                  </small>
                </summary>

                <div className="compact-dropdown-body">
                  <AnomalyPanel
                    anomalies={
                      anomalies === null
                        ? null
                        : displayedAnomalies
                    }
                  />
                </div>
              </details>

              {/* ======================================================
                  RECENT EVENTS
                  ====================================================== */}

              <details className="compact-dropdown">
                <summary>
                  <span>
                    Recent Events
                  </span>

                  <small>
                    {events
                      ? `${Math.min(
                          events.length,
                          20
                        )} shown`
                      : "loading"}
                  </small>
                </summary>

                <div className="compact-dropdown-body event-drawer-body">
                  <EventFeed
                    events={events}
                  />
                </div>
              </details>
            </div>

            {/* ========================================================
                CAROUSEL INDICATOR
                ======================================================== */}

            <div className="carousel-indicator">
              <span className="carousel-dot active" />

              <span className="carousel-dot" />

              <span className="carousel-indicator-text">
                Investigation overview
              </span>
            </div>
          </section>

          {/* ==========================================================
              PAGE 2 — BEHAVIORAL INSTABILITY
              ========================================================== */}

          <section className="carousel-page instability-page">
            <div className="instability-page-header">
              <button
                className="carousel-back"
                onClick={goToOverview}
                title="Back to investigation overview"
                aria-label="Back to investigation overview"
              >
                ‹
              </button>

              <div className="instability-heading">
                <div className="panel-title">
                  Behavioral Instability
                </div>

                <div className="panel-subtitle">
                  Simulated transition
                  stress from the active
                  What-If scenario
                </div>
              </div>

              <div className="instability-mode-pill">
                {whatifDeviations?.length
                  ? "WHAT-IF ACTIVE"
                  : "WAITING"}
              </div>
            </div>

            <div className="instability-page-stage">
              <div className="instability-visual-panel">
                <div className="instability-visual-header">
                  <span>
                    Dynamic behavior
                    field
                  </span>

                  <span className="instability-visual-meta">
                    Bubble size = deviation
                    magnitude
                  </span>
                </div>

                <InstabilityView
                  deviations={
                    whatifDeviations
                  }
                  width={980}
                  height={500}
                />
              </div>

              <div className="instability-explainer">
                <div className="instability-explainer-title">
                  How to read this
                </div>

                <div className="instability-legend">
                  <div className="legend-item">
                    <span className="legend-bubble low" />

                    <span>
                      <strong>
                        Flow Drift
                      </strong>

                      <small>
                        Small transition
                        deviation
                      </small>
                    </span>
                  </div>

                  <div className="legend-item">
                    <span className="legend-bubble medium" />

                    <span>
                      <strong>
                        Behavior Shift
                      </strong>

                      <small>
                        Meaningful routing
                        pressure
                      </small>
                    </span>
                  </div>

                  <div className="legend-item">
                    <span className="legend-bubble high" />

                    <span>
                      <strong>
                        Routing Surge
                      </strong>

                      <small>
                        Large simulated
                        deviation
                      </small>
                    </span>
                  </div>
                </div>

                <div className="instability-note">
                  These bubbles represent
                  simulated transition
                  stress produced by the
                  selected What-If
                  scenario. They are not a
                  claim that the real
                  application will fail in
                  exactly this way.
                </div>
              </div>
            </div>

            {/* ========================================================
                CAROUSEL INDICATOR
                ======================================================== */}

            <div className="carousel-indicator">
              <span className="carousel-dot" />

              <span className="carousel-dot active" />

              <span className="carousel-indicator-text">
                Behavioral instability
              </span>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}