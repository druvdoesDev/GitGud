import { useEffect, useRef, useCallback } from "react";

/**
 * useAutoRefresh — runs `callback` immediately on mount, then every
 * `intervalMs` milliseconds.  Returns a `refresh` function that triggers
 * an immediate re-run and resets the interval timer so the next automatic
 * refresh is a full `intervalMs` away.
 *
 * @param {() => void} callback   - async-safe function to call
 * @param {number}     intervalMs - refresh interval in milliseconds
 */
export function useAutoRefresh(callback, intervalMs) {
  const savedCallback = useRef(callback);
  const timerRef = useRef(null);

  // Keep ref current so the interval always calls the latest version
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  const start = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => savedCallback.current(), intervalMs);
  }, [intervalMs]);

  // Run immediately on mount, then start the interval
  useEffect(() => {
    savedCallback.current();
    start();
    return () => clearInterval(timerRef.current);
  }, [start]);

  // Manual refresh: run now and reset the timer
  const refresh = useCallback(() => {
    savedCallback.current();
    start();
  }, [start]);

  return refresh;
}
