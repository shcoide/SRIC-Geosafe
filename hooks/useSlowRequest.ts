import { useEffect, useState } from 'react';

/**
 * Flips to true once `active` has been true continuously for `delayMs`.
 * Resets as soon as `active` goes false. Used to swap a generic "loading"
 * spinner for a more informative message once a request has been pending
 * long enough to suggest a Render cold start rather than normal latency.
 */
export const useSlowRequest = (active: boolean, delayMs: number): boolean => {
  const [isSlow, setIsSlow] = useState(false);

  useEffect(() => {
    if (!active) {
      setIsSlow(false);
      return;
    }
    const timer = setTimeout(() => setIsSlow(true), delayMs);
    return () => clearTimeout(timer);
  }, [active, delayMs]);

  return isSlow;
};
