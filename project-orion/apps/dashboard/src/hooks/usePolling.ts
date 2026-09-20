import { useEffect, useRef } from 'react';

/**
 * Bounded polling hook with document visibility management.
 * Pauses background requests when tab/window is hidden to avoid duplicate polling
 * and preserve network/backend bandwidth.
 */
export function usePolling(
  callback: () => Promise<void> | void,
  intervalMs = 8000,
  enabled = true
): void {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled || intervalMs <= 0) {
      return;
    }

    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const execute = async () => {
      if (!isMounted) return;
      // Do not poll if the document is hidden
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      try {
        await savedCallback.current();
      } catch {
        // Errors handled within the individual page / callback
      }
    };

    // Run initial execution
    execute();

    // Set interval
    timerId = setInterval(execute, intervalMs);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        execute();
      }
    };

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', handleVisibilityChange);
    }

    return () => {
      isMounted = false;
      if (timerId !== null) {
        clearInterval(timerId);
      }
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      }
    };
  }, [intervalMs, enabled]);
}
