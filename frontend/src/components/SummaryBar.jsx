/**
 * SummaryBar — sessions / events / last-updated strip below the top bar.
 *
 * Props:
 *   summary: { total_sessions, total_events, last_updated } | null
 */
export default function SummaryBar({ summary }) {
  function formatTime(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso;
    }
  }

  return (
    <div className="summary-bar">
      <div className="summary-stat">
        <div className="summary-stat-label">Sessions</div>
        <div className="summary-stat-value">
          {summary ? summary.total_sessions : "—"}
        </div>
      </div>
      <div className="summary-stat">
        <div className="summary-stat-label">Events</div>
        <div className="summary-stat-value">
          {summary ? summary.total_events : "—"}
        </div>
      </div>
      <div className="summary-stat">
        <div className="summary-stat-label">Last Updated</div>
        <div className={`summary-stat-value ${summary?.last_updated ? "" : "muted"}`}>
          {summary ? formatTime(summary.last_updated) : "—"}
        </div>
      </div>
    </div>
  );
}
