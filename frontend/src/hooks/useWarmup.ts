import { useState, useEffect, useRef } from 'react';
import { API_URL } from '@/lib/api';

/**
 * Polls GET /health/warmup every 2 seconds until the backend signals ready.
 * Stops polling once ready — never restarts in the same session.
 */
export function useWarmup() {
  const [isReady, setIsReady] = useState(false);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const response = await fetch(`${API_URL}/health/warmup`);
        if (response.ok) {
          const data = await response.json();
          if (data.ready) {
            setIsReady(true);
            if (intervalRef.current !== null) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        }
      } catch {
        // Backend not reachable yet — keep polling
      }
    };

    check(); // immediate first check
    intervalRef.current = window.setInterval(check, 2000);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return { isReady };
}
