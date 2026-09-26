/**
 * WhatIfPanel — developer what-if scenario tool.
 *
 * Lets the developer:
 *   1. Pick an edge (from → to) from a dropdown populated by baseline data.
 *   2. Drag a slider to set a new probability for that edge.
 *   3. Click "Run Simulation" to POST /whatif/simulate.
 *   4. See the resulting deviations, completion delta, and distribution note.
 *
 * Props:
 *   baseline: { probabilities: { [from]: { [to]: number } } } | null
 *   onResult:  (WhatIfResult) => void   — called after a successful simulation
 */

import { useState } from "react";
import { postWhatifSimulate } from "../api/client.js";

// ── helpers ──────────────────────────────────────────────────────────────────

function edgesFromBaseline(baseline) {
  if (!baseline?.probabilities) return [];
  const edges = [];
  for (const [from, targets] of Object.entries(baseline.probabilities)) {
    for (const [to, prob] of Object.entries(targets)) {
      edges.push({ from, to, prob });
    }
  }
  edges.sort((a, b) =>
    a.from < b.from ? -1 : a.from > b.from ? 1 : a.to < b.to ? -1 : 1
  );
  return edges;
}

function fmtPct(v) {
  return `${(v * 100).toFixed(1)}%`;
}

function deltaClass(delta) {
  if (delta > 0.001) return "whatif-delta-pos";
  if (delta < -0.001) return "whatif-delta-neg";
  return "whatif-delta-zero";
}

// ── component ─────────────────────────────────────────────────────────────────

export default function WhatIfPanel({ baseline, onResult }) {
  const edges = edgesFromBaseline(baseline);

  const [selectedEdgeIdx, setSelectedEdgeIdx] = useState(0);
  const [sliderValue, setSliderValue] = useState(null); // null = unset, use baseline
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!baseline) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading baseline…
      </div>
    );
  }

  if (edges.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">📭</span>
        No edges yet — send some events first.
      </div>
    );
  }

  const selectedEdge = edges[selectedEdgeIdx] ?? edges[0];
  const baselineProb = selectedEdge.prob;
  const currentProb = sliderValue !== null ? sliderValue : baselineProb;

  function handleEdgeChange(e) {
    setSelectedEdgeIdx(Number(e.target.value));
    setSliderValue(null); // reset slider to baseline when edge changes
    setResult(null);
    setError(null);
  }

  function handleSlider(e) {
    setSliderValue(Number(e.target.value));
  }

  async function handleRun() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const data = await postWhatifSimulate({
        modifications: [
          { from: selectedEdge.from, to: selectedEdge.to, probability: currentProb },
        ],
        n_journeys: 200,
        rng_seed: 42,
      });
      setResult(data);
      if (onResult) onResult(data);
    } catch (err) {
      setError(err.message ?? "Simulation failed.");
    } finally {
      setRunning(false);
    }
  }

  const probChanged = Math.abs(currentProb - baselineProb) > 0.001;

  return (
    <div className="whatif-panel">
      {/* ── Edge picker ──────────────────────────────────────────────────── */}
      <div className="whatif-section">
        <label className="whatif-label" htmlFor="wi-edge-select">
          Edge to modify
        </label>
        <select
          id="wi-edge-select"
          className="whatif-select"
          value={selectedEdgeIdx}
          onChange={handleEdgeChange}
        >
          {edges.map((e, i) => (
            <option key={i} value={i}>
              {e.from} → {e.to}  ({fmtPct(e.prob)})
            </option>
          ))}
        </select>
      </div>

      {/* ── Probability slider ────────────────────────────────────────────── */}
      <div className="whatif-section">
        <label className="whatif-label">
          New probability
          <span className="whatif-prob-display">
            {fmtPct(currentProb)}
            {probChanged && (
              <span className={`whatif-prob-delta ${deltaClass(currentProb - baselineProb)}`}>
                {currentProb > baselineProb ? "▲" : "▼"}
                {fmtPct(Math.abs(currentProb - baselineProb))} vs baseline
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
          <span className="whatif-baseline-tick" style={{ left: `${baselineProb * 100}%` }}>
            baseline {fmtPct(baselineProb)}
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* ── Run button ────────────────────────────────────────────────────── */}
      <button
        className="whatif-run-btn"
        onClick={handleRun}
        disabled={running || !probChanged}
        title={!probChanged ? "Move the slider to change the probability first" : ""}
      >
        {running ? "Simulating…" : "▶ Run Simulation"}
      </button>

      {error && (
        <div className="whatif-error">⚠ {error}</div>
      )}

      {/* ── Results ──────────────────────────────────────────────────────── */}
      {result && <WhatIfResults result={result} />}
    </div>
  );
}

// ── Results sub-component ─────────────────────────────────────────────────────

function WhatIfResults({ result }) {
  const {
    deviations,
    completion_delta,
    journey_stats_baseline,
    journey_stats_whatif,
    distribution_comparison,
  } = result;

  const completionDeltaPct = completion_delta != null
    ? (completion_delta * 100).toFixed(1)
    : null;

  return (
    <div className="whatif-results">
      {/* ── Stats row ──────────────────────────────────────────────────── */}
      <div className="whatif-stats-row">
        <div className="whatif-stat">
          <div className="whatif-stat-label">Completion Δ</div>
          <div className={`whatif-stat-value ${deltaClass(completion_delta)}`}>
            {completion_delta > 0 ? "+" : ""}{completionDeltaPct}%
          </div>
        </div>
        <div className="whatif-stat">
          <div className="whatif-stat-label">Baseline rate</div>
          <div className="whatif-stat-value">
            {journey_stats_baseline
              ? `${(journey_stats_baseline.completion_rate * 100).toFixed(1)}%`
              : "—"}
          </div>
        </div>
        <div className="whatif-stat">
          <div className="whatif-stat-label">What-if rate</div>
          <div className="whatif-stat-value">
            {journey_stats_whatif
              ? `${(journey_stats_whatif.completion_rate * 100).toFixed(1)}%`
              : "—"}
          </div>
        </div>
      </div>

      {/* ── Deviations table ───────────────────────────────────────────── */}
      {deviations.length > 0 && (
        <>
          <div className="whatif-section-title">Edge deviations</div>
          <table className="whatif-dev-table">
            <thead>
              <tr>
                <th>Edge</th>
                <th>Baseline</th>
                <th>What-if</th>
                <th>Δ</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {deviations.map((d, i) => (
                <tr key={i} className={`whatif-dev-row wi-sev-${d.severity}`}>
                  <td className="whatif-dev-edge">
                    {d.from} → {d.to}
                  </td>
                  <td>{fmtPct(d.baseline_probability)}</td>
                  <td>{fmtPct(d.whatif_probability)}</td>
                  <td className={deltaClass(d.absolute_delta)}>
                    {d.absolute_delta > 0 ? "+" : ""}
                    {fmtPct(d.absolute_delta)}
                  </td>
                  <td>
                    <span className={`anomaly-badge ${d.severity}`}>{d.severity}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* ── Chi-square note ────────────────────────────────────────────── */}
      {distribution_comparison && (
        <div className="whatif-chi-note">
          {distribution_comparison.note}
        </div>
      )}
    </div>
  );
}
