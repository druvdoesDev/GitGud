import { useState } from "react";
import { postWhatifSimulate } from "../api/client.js";

function edgesFromBaseline(baseline) {
  if (!baseline?.probabilities) return [];

  const edges = [];

  for (const [from, targets] of Object.entries(
    baseline.probabilities
  )) {
    for (const [to, probability] of Object.entries(
      targets
    )) {
      edges.push({
        from,
        to,
        prob: probability,
      });
    }
  }

  edges.sort((a, b) => {
    if (a.from !== b.from) {
      return a.from.localeCompare(b.from);
    }

    return a.to.localeCompare(b.to);
  });

  return edges;
}

function fmtPct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function deltaClass(delta) {
  if (delta > 0.001) {
    return "whatif-delta-pos";
  }

  if (delta < -0.001) {
    return "whatif-delta-neg";
  }

  return "whatif-delta-zero";
}

const SCENARIOS = {
  manual: {
    label: "Manual probability change",
  },

  spike: {
    label: "Traffic spike (+25%)",
    apply: (baseline) =>
      Math.min(1, baseline + 0.25),
  },

  drop: {
    label: "Traffic drop (-25%)",
    apply: (baseline) =>
      Math.max(0, baseline - 0.25),
  },

  dropout: {
    label: "Hard dropout (0%)",
    apply: () => 0,
  },

  surge: {
    label: "Routing surge (+50%)",
    apply: (baseline) =>
      Math.min(1, baseline + 0.5),
  },
};

export default function WhatIfPanel({
  baseline,
  onResult,
}) {
  const edges = edgesFromBaseline(baseline);

  const [selectedEdgeIdx, setSelectedEdgeIdx] =
    useState(0);

  const [scenario, setScenario] =
    useState("manual");

  const [sliderValue, setSliderValue] =
    useState(null);

  const [running, setRunning] =
    useState(false);

  const [error, setError] =
    useState(null);

  const [result, setResult] =
    useState(null);

  if (!baseline) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">
          ⏳
        </span>

        Loading baseline…
      </div>
    );
  }

  if (edges.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">
          📭
        </span>

        No transitions available yet.
      </div>
    );
  }

  const selectedEdge =
    edges[selectedEdgeIdx] ?? edges[0];

  const baselineProb =
    selectedEdge.prob;

  const scenarioValue =
    scenario !== "manual"
      ? SCENARIOS[scenario].apply(
          baselineProb
        )
      : null;

  const currentProb =
    scenarioValue !== null
      ? scenarioValue
      : sliderValue !== null
        ? sliderValue
        : baselineProb;

  function handleEdgeChange(event) {
    setSelectedEdgeIdx(
      Number(event.target.value)
    );

    setSliderValue(null);
    setScenario("manual");
    setResult(null);
    setError(null);
  }

  function handleScenarioChange(event) {
    const nextScenario =
      event.target.value;

    setScenario(nextScenario);
    setSliderValue(null);
    setResult(null);
    setError(null);
  }

  function handleSlider(event) {
    setScenario("manual");
    setSliderValue(
      Number(event.target.value)
    );

    setResult(null);
  }

  async function handleRun() {
    setRunning(true);
    setError(null);

    try {
      const data =
        await postWhatifSimulate({
          modifications: [
            {
              from: selectedEdge.from,
              to: selectedEdge.to,
              probability: currentProb,
            },
          ],

          n_journeys: 200,
          rng_seed: 42,
        });

      setResult(data);

      if (onResult) {
        onResult(data);
      }
    } catch (err) {
      setError(
        err.message ??
          "Simulation failed."
      );
    } finally {
      setRunning(false);
    }
  }

  const changed =
    Math.abs(
      currentProb - baselineProb
    ) > 0.001;

  return (
    <div className="whatif-panel">

      {/* Edge */}
      <div className="whatif-section">
        <label
          className="whatif-label"
          htmlFor="wi-edge-select"
        >
          Edge to modify
        </label>

        <select
          id="wi-edge-select"
          className="whatif-select"
          value={selectedEdgeIdx}
          onChange={handleEdgeChange}
        >
          {edges.map((edge, index) => (
            <option
              key={index}
              value={index}
            >
              {edge.from} → {edge.to}{" "}
              ({fmtPct(edge.prob)})
            </option>
          ))}
        </select>
      </div>

      {/* Scenario */}
      <div className="whatif-section">
        <label
          className="whatif-label"
          htmlFor="wi-scenario"
        >
          Scenario anomaly
        </label>

        <select
          id="wi-scenario"
          className="whatif-select"
          value={scenario}
          onChange={handleScenarioChange}
        >
          {Object.entries(
            SCENARIOS
          ).map(
            ([value, item]) => (
              <option
                key={value}
                value={value}
              >
                {item.label}
              </option>
            )
          )}
        </select>

        <div className="whatif-helper">
          Preset scenarios change the selected
          transition before simulation.
        </div>
      </div>

      {/* Probability */}
      <div className="whatif-section">
        <label className="whatif-label">
          New probability

          <span className="whatif-prob-display">
            {fmtPct(currentProb)}

            {changed && (
              <span
                className={`whatif-prob-delta ${deltaClass(
                  currentProb -
                    baselineProb
                )}`}
              >
                {currentProb >
                baselineProb
                  ? "▲"
                  : "▼"}

                {fmtPct(
                  Math.abs(
                    currentProb -
                      baselineProb
                  )
                )}{" "}
                vs baseline
              </span>
            )}
          </span>
        </label>

        <input
          type="range"
          className="whatif-slider"
          min={0}
          max={1}
          step={0.01}
          value={currentProb}
          onChange={handleSlider}
        />

        <div className="whatif-slider-labels">
          <span>0%</span>

          <span
            className="whatif-baseline-tick"
            style={{
              left: `${baselineProb * 100}%`,
            }}
          >
            baseline{" "}
            {fmtPct(baselineProb)}
          </span>

          <span>100%</span>
        </div>
      </div>

      {/* Run */}
      <button
        className="whatif-run-btn"
        onClick={handleRun}
        disabled={
          running || !changed
        }
      >
        {running
          ? "⟳ Simulating…"
          : "▶ Run Simulation"}
      </button>

      {error && (
        <div className="whatif-error">
          ⚠ {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <WhatIfResults result={result} />
      )}
    </div>
  );
}

function WhatIfResults({
  result,
}) {
  const {
    deviations,
    completion_delta,
    journey_stats_baseline,
    journey_stats_whatif,
    distribution_comparison,
  } = result;

  return (
    <div className="whatif-results">

      <div className="scenario-result-banner">
        Scenario applied to behavioral model
      </div>

      <div className="whatif-stats-row">
        <div className="whatif-stat">
          <div className="whatif-stat-label">
            Completion Δ
          </div>

          <div
            className={`whatif-stat-value ${deltaClass(
              completion_delta
            )}`}
          >
            {completion_delta > 0
              ? "+"
              : ""}
            {(
              completion_delta *
              100
            ).toFixed(1)}
            %
          </div>
        </div>

        <div className="whatif-stat">
          <div className="whatif-stat-label">
            Baseline
          </div>

          <div className="whatif-stat-value">
            {journey_stats_baseline
              ? fmtPct(
                  journey_stats_baseline
                    .completion_rate
                )
              : "—"}
          </div>
        </div>

        <div className="whatif-stat">
          <div className="whatif-stat-label">
            What-if
          </div>

          <div className="whatif-stat-value">
            {journey_stats_whatif
              ? fmtPct(
                  journey_stats_whatif
                    .completion_rate
                )
              : "—"}
          </div>
        </div>
      </div>

      {deviations?.length > 0 && (
        <>
          <div className="whatif-section-title">
            Edge deviations
          </div>

          <div className="whatif-deviation-list">
            {deviations.map(
              (deviation, index) => (
                <div
                  key={index}
                  className={`whatif-deviation ${deviation.severity}`}
                >
                  <div className="deviation-edge">
                    {deviation.from} →{" "}
                    {deviation.to}
                  </div>

                  <div className="deviation-values">
                    <span>
                      {fmtPct(
                        deviation
                          .baseline_probability
                      )}
                    </span>

                    <span>→</span>

                    <strong>
                      {fmtPct(
                        deviation
                          .whatif_probability
                      )}
                    </strong>

                    <span
                      className={deltaClass(
                        deviation
                          .absolute_delta
                      )}
                    >
                      {deviation
                        .absolute_delta >
                      0
                        ? "+"
                        : ""}
                      {fmtPct(
                        deviation
                          .absolute_delta
                      )}
                    </span>

                    <span
                      className={`anomaly-badge ${deviation.severity}`}
                    >
                      {deviation.severity}
                    </span>
                  </div>
                </div>
              )
            )}
          </div>
        </>
      )}

      {distribution_comparison && (
        <div className="whatif-chi-note">
          {
            distribution_comparison.note
          }
        </div>
      )}
    </div>
  );
}