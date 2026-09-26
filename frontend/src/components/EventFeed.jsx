/**
 * EventFeed — most recent 20 events, newest first.
 *
 * Props:
 *   events: [{ session_id, timestamp, page, event, properties }] | null
 */
export default function EventFeed({ events }) {
  if (!events) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">⏳</span>
        Loading events…
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">📡</span>
        <strong>No events yet</strong>
        <span>Open the sample app and navigate around.</span>
      </div>
    );
  }

  // Reverse to show newest first; take at most 20
  const recent = [...events].reverse().slice(0, 20);

  function formatTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso;
    }
  }

  return (
    <div className="event-feed">
      {recent.map((ev, i) => (
        <div key={i} className="event-row">
          <span className="event-ts">{formatTime(ev.timestamp)}</span>
          <span className="event-sid">{ev.session_id.slice(0, 8)}</span>
          <span className="event-page">{ev.page}</span>
          <span className="event-name">{ev.event}</span>
        </div>
      ))}
    </div>
  );
}
