import { useEffect, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

/**
 * Ordered left-to-right layout for the known e-commerce pages.
 * Positions are expressed as column indices; actual pixel x/y are computed
 * at render time based on the number of nodes so the graph fills the canvas
 * regardless of how many pages are present.
 */
const KNOWN_ORDER = ["home", "product", "cart", "checkout", "confirmation"];

/**
 * Assign a column index to every node.
 * Known pages get their fixed column; unknown pages are placed in extra
 * columns after the last known page, one per row of two.
 */
function assignColumns(nodes) {
  const columns = {};
  const unknowns = [];

  for (const n of nodes) {
    const idx = KNOWN_ORDER.indexOf(n.id);
    if (idx !== -1) {
      columns[n.id] = { col: idx, row: 0 };
    } else {
      unknowns.push(n.id);
    }
  }

  const baseCol = KNOWN_ORDER.length;
  unknowns.forEach((id, i) => {
    columns[id] = { col: baseCol + Math.floor(i / 2), row: i % 2 };
  });

  return columns;
}

const H_GAP = 200; // horizontal gap between columns (px)
const V_GAP = 120; // vertical gap between rows (px)
const NODE_H = 40; // approximate node height (px)

function buildPositions(nodes) {
  const layout = assignColumns(nodes);
  return Object.fromEntries(
    Object.entries(layout).map(([id, { col, row }]) => [
      id,
      { x: col * H_GAP, y: row * (NODE_H + V_GAP) },
    ])
  );
}

/** Map visit_count to a node width for visual sizing. */
function nodeWidth(count) {
  if (!count || count === 0) return 100;
  if (count < 10) return 100;
  if (count < 30) return 120;
  return 140;
}

/** Map transition count to edge stroke width. */
function edgeStroke(count) {
  if (!count || count <= 1) return 1.5;
  if (count < 10) return 2.5;
  return 4;
}

// ── Inner component that has access to useReactFlow ─────────────────────────

function GraphViewInner({ graph }) {
  const { fitView } = useReactFlow();

  // Re-fit whenever the graph data changes (new nodes/edges after refresh)
  useEffect(() => {
    if (graph && graph.nodes.length > 0) {
      // Small delay lets ReactFlow finish rendering the new nodes before fitting
      const t = setTimeout(() => fitView({ padding: 0.25, duration: 300 }), 50);
      return () => clearTimeout(t);
    }
  }, [graph, fitView]);

  const handleFit = useCallback(() => {
    fitView({ padding: 0.25, duration: 300 });
  }, [fitView]);

  if (!graph) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading graph…
      </div>
    );
  }

  if (graph.nodes.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">🔍</span>
        <strong>No behavioral data yet</strong>
        <span>Generate events in the sample app, then refresh.</span>
      </div>
    );
  }

  const positions = buildPositions(graph.nodes);

  const rfNodes = graph.nodes.map((n) => {
    const pos = positions[n.id] ?? { x: 0, y: 0 };
    const w = nodeWidth(n.visit_count);
    return {
      id: n.id,
      position: pos,
      data: { label: n.id, count: n.visit_count },
      style: {
        width: w,
        background: "#fff",
        border: "1.5px solid #3b82d4",
        borderRadius: 8,
        fontSize: 12,
        fontWeight: 700,
        textAlign: "center",
        padding: "6px 4px",
      },
    };
  });

  const rfEdges = graph.edges.map((e) => ({
    id: `${e.from}-${e.to}`,
    source: e.from,
    target: e.to,
    label: `${(e.probability * 100).toFixed(0)}%`,
    labelStyle: { fontSize: 10, fill: "#57606a", fontWeight: 600 },
    labelBgStyle: { fill: "#f6f8fa", fillOpacity: 0.9 },
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed, color: "#3b82d4" },
    style: {
      strokeWidth: edgeStroke(e.count),
      stroke: "#3b82d4",
    },
  }));

  return (
    <div className="graph-wrap" style={{ position: "relative" }}>
      {/* Fit-to-view button overlaid on the graph */}
      <button
        onClick={handleFit}
        title="Fit graph to view"
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          zIndex: 10,
          padding: "3px 10px",
          fontSize: "0.75rem",
          fontWeight: 600,
          background: "#fff",
          border: "1px solid #d0d7de",
          borderRadius: 5,
          cursor: "pointer",
          color: "#1f2328",
        }}
      >
        ⊡ Fit
      </button>

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor="#3b82d4"
          nodeStrokeWidth={0}
          style={{ border: "1px solid #d0d7de" }}
        />
      </ReactFlow>
    </div>
  );
}

// ── Public export wraps the inner component in ReactFlowProvider ─────────────

/**
 * GraphView — behavioral transition graph.
 *
 * Props:
 *   graph: { nodes: [{id, visit_count}], edges: [{from, to, probability, count}] } | null
 *
 * Changes from original:
 *   - fitView re-fires on every graph data change (not just mount)
 *   - node positions are column-based and viewport-relative, not hardcoded pixels
 *   - unknown-page positioning bug fixed (was always passing index 0)
 *   - Fit button added (programmatic fitView via useReactFlow)
 *   - elementsSelectable enabled (nodes can be clicked/highlighted)
 *   - wrapped in ReactFlowProvider so useReactFlow() works correctly
 */
export default function GraphView({ graph }) {
  return (
    <ReactFlowProvider>
      <GraphViewInner graph={graph} />
    </ReactFlowProvider>
  );
}
