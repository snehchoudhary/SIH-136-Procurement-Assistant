import { useEffect, useRef, useState } from 'react';

/**
 * Animates a number from its previous value to the new target using requestAnimationFrame.
 * Returns the current animated value (null when target is null).
 */
export function useAnimatedNumber(target: number | null, duration = 600): number | null {
  const [current, setCurrent] = useState<number | null>(target);
  const prevRef = useRef<number | null>(target);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (target === null) {
      prevRef.current = null;
      setCurrent(null);
      return;
    }

    const from = prevRef.current ?? target;
    const startTime = performance.now();

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = from + (target - from) * eased;
      setCurrent(value);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        prevRef.current = target;
        rafRef.current = null;
      }
    };

    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [target, duration]);

  return current;
}
