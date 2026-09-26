/**
 * StatusBar — API connectivity indicator shown in the top bar.
 *
 * Props:
 *   status: "ok" | "error" | "loading"
 */
export default function StatusBar({ status }) {
  const label =
    status === "ok"      ? "Connected" :
    status === "error"   ? "API Unavailable" :
                           "Connecting…";

  return (
    <div className="status-indicator">
      <span className={`status-dot ${status}`} />
      {label}
    </div>
  );
}
