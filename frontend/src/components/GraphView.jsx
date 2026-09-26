import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

/**
 * Deterministic left-to-right positions for the known e-commerce pages.
 * Unknown pages fall back to a row below the main flow.
 */
const KNOWN_POSITIONS = {
  home:         { x: 40,  y: 200 },
  product:      { x: 220, y: 200 },
  cart:         { x: 400, y: 200 },
  checkout:     { x: 580, y: 200 },
  confirmation: { x: 760, y: 200 },
};

function getPosition(id, unknownIndex) {
  return KNOWN_POSITIONS[id] ?? { x: 40 + unknownIndex * 180, y: 380 };
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

/**
 * GraphView — behavioral transition graph.
 *
 * Props:
 *   graph: { nodes: [{id, visit_count}], edges: [{from, to, probability, count}] } | null
 */
export default function GraphView({ graph }) {
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

  // Track unknown pages to position them in a grid row below
  let unknownIdx = 0;
  const knownIds = new Set(Object.keys(KNOWN_POSITIONS));

  const rfNodes = graph.nodes.map((n) => {
    const isUnknown = !knownIds.has(n.id);
    const pos = getPosition(n.id, isUnknown ? unknownIdx++ : 0);
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
    <div className="graph-wrap">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={false}
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
