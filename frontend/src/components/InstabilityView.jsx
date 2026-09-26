/**
 * InstabilityView — canvas bubble-physics visualization of what-if deviations.
 *
 * Each bubble represents a directed edge (from → to).
 * Visual encoding:
 *   - Radius:  r = 15 + (60 - 15) × magnitude       (15–60 px)
 *   - Speed:   v = 0.3 + 3.0 × magnitude px/frame at ~60fps
 *   - Color:   low=blue, medium=orange, high=red
 *   - Label:   "from→to\nΔ +X.X%"
 * Escape condition:
 *   - magnitude ≥ 0.30 → bubble leaves the container; container gets red border.
 *   - Escaped bubbles render at their out-of-bounds position with 0.4 opacity.
 *
 * Props:
 *   deviations: EdgeDeviation[] | null   (from WhatIfResult.deviations)
 *   width:  number (default 380)
 *   height: number (default 280)
 */

import { useEffect, useRef, useCallback } from "react";

// ── physics constants ─────────────────────────────────────────────────────────

const R_MIN = 15;
const R_MAX = 60;
const V_MIN = 0.3;
const V_MAX = 3.3;
const ESCAPE_THRESHOLD = 0.30;

function radiusFor(magnitude) {
  return R_MIN + (R_MAX - R_MIN) * Math.min(magnitude, 1);
}

function speedFor(magnitude) {
  return V_MIN + (V_MAX - V_MIN) * Math.min(magnitude, 1);
}

function colorFor(severity) {
  if (severity === "high")   return "#cf222e";
  if (severity === "medium") return "#d97706";
  return "#3b82d4";
}

// ── seeded deterministic position / direction ─────────────────────────────────

function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seedFromEdge(from, to) {
  const s = `${from}→${to}`;
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = (Math.imul(h, 16777619)) >>> 0;
  }
  return h;
}

function makeBubble(dev, width, height) {
  const seed = seedFromEdge(dev.from, dev.to);
  const rng = mulberry32(seed);

  const r = radiusFor(dev.magnitude);
  const speed = speedFor(dev.magnitude);
  const angle = rng() * Math.PI * 2;

  return {
    from: dev.from,
    to: dev.to,
    magnitude: dev.magnitude,
    severity: dev.severity,
    absolute_delta: dev.absolute_delta,
    r,
    color: colorFor(dev.severity),
    x: r + rng() * (width - 2 * r),
    y: r + rng() * (height - 2 * r),
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    escaped: dev.magnitude >= ESCAPE_THRESHOLD,
  };
}

// ── component ─────────────────────────────────────────────────────────────────

export default function InstabilityView({
  deviations,
  width = 380,
  height = 280,
}) {
  const canvasRef = useRef(null);
  const bubblesRef = useRef([]);
  const rafRef = useRef(null);
  const escapedRef = useRef(false);

  // Build bubbles whenever deviations change
  useEffect(() => {
    if (!deviations || deviations.length === 0) {
      bubblesRef.current = [];
      escapedRef.current = false;
      return;
    }
    const bubbles = deviations.map((d) => makeBubble(d, width, height));
    bubblesRef.current = bubbles;
    escapedRef.current = bubbles.some((b) => b.escaped);
  }, [deviations, width, height]);

  // Animation loop
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    for (const b of bubblesRef.current) {
      if (b.escaped) {
        // Let escaped bubbles drift off-canvas — just update position
        b.x += b.vx;
        b.y += b.vy;
      } else {
        // Normal bounce off walls
        b.x += b.vx;
        b.y += b.vy;
        if (b.x - b.r < 0)      { b.x = b.r;          b.vx = Math.abs(b.vx); }
        if (b.x + b.r > width)  { b.x = width - b.r;  b.vx = -Math.abs(b.vx); }
        if (b.y - b.r < 0)      { b.y = b.r;          b.vy = Math.abs(b.vy); }
        if (b.y + b.r > height) { b.y = height - b.r; b.vy = -Math.abs(b.vy); }
      }

      const opacity = b.escaped ? 0.4 : 1.0;

      // Fill
      ctx.globalAlpha = opacity * 0.18;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.fillStyle = b.color;
      ctx.fill();

      // Stroke
      ctx.globalAlpha = opacity * 0.9;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.strokeStyle = b.color;
      ctx.lineWidth = b.escaped ? 1.5 : 2;
      ctx.stroke();

      // Label
      ctx.globalAlpha = opacity;
      ctx.fillStyle = b.color;
      ctx.font = `bold ${Math.max(9, b.r * 0.28)}px system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const label = `${b.from}→${b.to}`;
      const delta = `${b.absolute_delta >= 0 ? "+" : ""}${(b.absolute_delta * 100).toFixed(1)}%`;
      ctx.fillText(label, b.x, b.y - 5);
      ctx.font = `${Math.max(8, b.r * 0.22)}px system-ui, sans-serif`;
      ctx.fillText(delta, b.x, b.y + 8);

      ctx.globalAlpha = 1.0;
    }

    rafRef.current = requestAnimationFrame(draw);
  }, [width, height]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [draw]);

  const hasEscaped = escapedRef.current || (bubblesRef.current.some((b) => b.escaped));
  const isEmpty = !deviations || deviations.length === 0;

  return (
    <div
      className={`instability-wrap${hasEscaped ? " instability-escaped" : ""}`}
      style={{ width, height: isEmpty ? "auto" : height }}
    >
      {isEmpty ? (
        <div className="empty-state" style={{ minHeight: 100 }}>
          <span className="empty-state-icon">🫧</span>
          Run a simulation to see behavioral instability
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="instability-canvas"
        />
      )}
    </div>
  );
}
