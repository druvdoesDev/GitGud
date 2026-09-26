/**
 * FlowTable — ranked user journey table.
 *
 * Props:
 *   flows: [{ path: string[], count: number, share: number }] | null
 */
export default function FlowTable({ flows }) {
  if (!flows) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading flows…
      </div>
    );
  }

  if (flows.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">🗺️</span>
        No user flows yet
      </div>
    );
  }

  return (
    <table className="flow-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Path</th>
          <th style={{ textAlign: "right" }}>Sessions</th>
          <th style={{ textAlign: "right" }}>Share</th>
        </tr>
      </thead>
      <tbody>
        {flows.map((flow, i) => (
          <tr key={flow.path.join(">")} className={i === 0 ? "flow-primary" : ""}>
            <td style={{ color: "#57606a" }}>{i + 1}</td>
            <td>
              <div className="flow-path">
                {flow.path.map((page, j) => (
                  <span key={j} style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}>
                    <span className="flow-page">{page}</span>
                    {j < flow.path.length - 1 && (
                      <span className="flow-arrow">›</span>
                    )}
                  </span>
                ))}
              </div>
            </td>
            <td style={{ textAlign: "right" }}>{flow.count}</td>
            <td style={{ textAlign: "right" }} className="flow-share">
              {(flow.share * 100).toFixed(1)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
