import { useEffect, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

const KNOWN_ORDER = [
  "home",
  "product",
  "cart",
  "checkout",
  "confirmation",
];

const H_GAP = 190;
const V_GAP = 130;

function assignColumns(nodes) {
  const result = {};
  const unknown = [];

  for (const node of nodes) {
    const index = KNOWN_ORDER.indexOf(node.id);

    if (index >= 0) {
      result[node.id] = {
        col: index,
        row: 0,
      };
    } else {
      unknown.push(node.id);
    }
  }

  const base = KNOWN_ORDER.length;

  unknown.forEach((id, index) => {
    result[id] = {
      col: base + Math.floor(index / 2),
      row: index % 2,
    };
  });

  return result;
}

function buildPositions(nodes) {
  const layout = assignColumns(nodes);

  return Object.fromEntries(
    Object.entries(layout).map(([id, value]) => [
      id,
      {
        x: value.col * H_GAP,
        y: value.row * V_GAP,
      },
    ])
  );
}

function getNodeWidth(count) {
  if (count >= 30) return 150;
  if (count >= 10) return 135;
  return 120;
}

function getEdgeWidth(count) {
  if (count >= 10) return 3.5;
  if (count >= 5) return 2.5;
  return 1.8;
}

function getTheme() {
  const dark = document.documentElement.dataset.theme === "dark";

  return {
    dark,
    nodeBackground: dark ? "#303844" : "#ffffff",
    nodeBorder: dark ? "#6ea8ff" : "#3578d4",
    nodeText: dark ? "#f2f6fb" : "#17202a",
    nodeMuted: dark ? "#aab5c2" : "#66717f",
    edge: dark ? "#78aeff" : "#3578d4",
    edgeLabelBackground: dark ? "#20262d" : "#ffffff",
    edgeLabelText: dark ? "#e8edf3" : "#17202a",
    graphBackground: dark ? "#20262d" : "#ffffff",
    positive: dark ? "#4ec77b" : "#2e9c57",
    negative: dark ? "#ff7078" : "#d94a53",
  };
}

function BehavioralNode({ data }) {
  return (
    <div
      style={{
        position: "relative",
        minWidth: data.width,
        minHeight: 54,
        padding: "8px 12px",
        borderRadius: 12,
        border: `1.5px solid ${data.border}`,
        background: data.background,
        color: data.color,
        boxShadow: data.selected
          ? `0 0 0 3px ${data.border}33, 0 7px 20px rgba(0,0,0,.15)`
          : "0 4px 14px rgba(0,0,0,.08)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 3,
        transition:
          "background .2s ease, border-color .2s ease, box-shadow .2s ease",
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          width: 7,
          height: 7,
          background: data.border,
          border: "2px solid transparent",
        }}
      />

      <div
        style={{
          fontSize: 13,
          fontWeight: 800,
          lineHeight: 1.1,
          letterSpacing: "-0.01em",
        }}
      >
        {data.label}
      </div>

      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          color: data.muted,
        }}
      >
        {data.count} visits
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          width: 7,
          height: 7,
          background: data.border,
          border: "2px solid transparent",
        }}
      />
    </div>
  );
}

const nodeTypes = {
  behavioral: BehavioralNode,
};

function GraphViewInner({
  graph,
  whatIfProbabilities = null,
}) {
  const { fitView } = useReactFlow();

  const theme = useMemo(() => getTheme(), [graph, whatIfProbabilities]);

  const positions = useMemo(
    () => (graph ? buildPositions(graph.nodes) : {}),
    [graph]
  );

  useEffect(() => {
    if (!graph || graph.nodes.length === 0) return;

    const timer = setTimeout(() => {
      fitView({
        padding: 0.24,
        duration: 350,
      });
    }, 60);

    return () => clearTimeout(timer);
  }, [graph, whatIfProbabilities, fitView]);

  const handleFit = useCallback(() => {
    fitView({
      padding: 0.24,
      duration: 350,
    });
  }, [fitView]);

  if (!graph) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading graph…
      </div>
    );
  }

  if (!graph.nodes?.length) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">🔍</span>
        <strong>No behavioral data yet</strong>
        <span>
          Generate events in the sample app, then refresh.
        </span>
      </div>
    );
  }

  const rfNodes = graph.nodes.map((node) => {
    const position = positions[node.id] ?? { x: 0, y: 0 };

    return {
      id: node.id,
      type: "behavioral",
      position,

      data: {
        label: node.id,
        count: node.visit_count ?? 0,
        width: getNodeWidth(node.visit_count ?? 0),
        background: theme.nodeBackground,
        border: theme.nodeBorder,
        color: theme.nodeText,
        muted: theme.nodeMuted,
      },

      draggable: true,
      selectable: true,
    };
  });

  const rfEdges = graph.edges.map((edge) => {
    const baselineProbability = Number(edge.probability ?? 0);

    const modifiedProbability =
      whatIfProbabilities?.[edge.from]?.[edge.to] ??
      baselineProbability;

    const delta = modifiedProbability - baselineProbability;
    const changed = Math.abs(delta) > 0.0005;

    const stroke =
      !changed
        ? theme.edge
        : delta > 0
        ? theme.positive
        : theme.negative;

    return {
      id: `${edge.from}-${edge.to}`,

      source: edge.from,
      target: edge.to,

      type: "default",

      label: `${(modifiedProbability * 100).toFixed(0)}%`,

      animated: changed,

      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: stroke,
      },

      labelStyle: {
        fontSize: 11,
        fontWeight: 800,
        fill: theme.edgeLabelText,
      },

      labelBgStyle: {
        fill: theme.edgeLabelBackground,
        fillOpacity: 0.96,
        stroke: theme.dark ? "#3a444f" : "#d7dee7",
        strokeWidth: 1,
      },

      style: {
        stroke,
        strokeWidth:
          changed
            ? Math.max(getEdgeWidth(edge.count), 3)
            : getEdgeWidth(edge.count),
        strokeDasharray: changed ? "7 5" : undefined,
      },
    };
  });

  return (
    <div
      className="graph-wrap"
      style={{
        position: "relative",
        background: theme.graphBackground,
      }}
    >
      <button
        type="button"
        className="graph-fit-button"
        onClick={handleFit}
        title="Fit graph to view"
      >
        ⊡ Fit
      </button>

      {whatIfProbabilities && (
        <div
          className="graph-scenario-badge"
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            zIndex: 10,
            padding: "4px 8px",
            borderRadius: 999,
            border: `1px solid ${theme.positive}`,
            background: theme.dark ? "#25352d" : "#f0fff5",
            color: theme.positive,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: ".05em",
          }}
        >
          WHAT-IF ACTIVE
        </div>
      )}

      {!whatIfProbabilities && (
        <div
          className="graph-scenario-badge"
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            zIndex: 10,
            padding: "4px 8px",
            borderRadius: 999,
            border: `1px solid ${theme.nodeMuted}55`,
            background: theme.dark ? "#293039" : "#f8fafc",
            color: theme.nodeMuted,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: ".05em",
          }}
        >
          BASELINE
        </div>
      )}

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{
          padding: 0.24,
        }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        proOptions={{
          hideAttribution: true,
        }}
      >
        <Background
          color={theme.dark ? "#3a444f" : "#dfe5ec"}
          gap={20}
        />

        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default function GraphView(props) {
  return (
    <ReactFlowProvider>
      <GraphViewInner {...props} />
    </ReactFlowProvider>
  );
}