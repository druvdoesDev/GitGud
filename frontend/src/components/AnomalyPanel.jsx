/**
 * AnomalyPanel — list of behavioral anomalies from the BI layer.
 * Currently always empty (anomaly_detection.py is not yet implemented).
 * Will populate automatically once the BI team implements it.
 *
 * Props:
 *   anomalies: [{ type, description, severity }] | null
 */
export default function AnomalyPanel({ anomalies }) {
  if (!anomalies) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading…
      </div>
    );
  }

  if (anomalies.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">✅</span>
        No anomalies detected
      </div>
    );
  }

  return (
    <ul className="anomaly-list">
      {anomalies.map((a, i) => (
        <li key={i} className="anomaly-item">
          <span className={`anomaly-badge ${a.severity}`}>{a.severity}</span>
          <span>
            <strong>{a.type}</strong> — {a.description}
          </span>
        </li>
      ))}
    </ul>
  );
}
