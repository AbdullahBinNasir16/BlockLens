import { useEffect, useRef, useState, useCallback } from 'react';

/** Fires once when the element first enters the viewport. Cheap: one
 *  observer per element, disconnected immediately after firing. */
export function useInView<T extends HTMLElement>(
  rootMargin = '0px 0px -12% 0px'
): [React.RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    if (typeof IntersectionObserver === 'undefined') {
      setSeen(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { rootMargin, threshold: 0.05 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [seen, rootMargin]);

  return [ref, seen];
}

/** rAF-driven scroll progress for a section, 0 → 1 as it crosses the
 *  viewport. Reads layout once per frame and only while on screen. */
export function useScrollProgress<T extends HTMLElement>(): [
  React.RefObject<T>,
  number
] {
  const ref = useRef<T>(null);
  const [p, setP] = useState(0);
  const raf = useRef(0);
  const active = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      raf.current = 0;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      /* Tall sections (a sticky scene) progress across their own scroll
         distance. Sections shorter than the viewport have no such distance,
         so they progress as they leave the top of the screen instead —
         which is what a hero wants: 0 at rest, 1 one screen later. */
      const total = r.height - vh;
      const span = total > 0 ? total : Math.max(1, r.height);
      setP(Math.min(1, Math.max(0, -r.top / span)));
    };

    const onScroll = () => {
      if (!active.current || raf.current) return;
      raf.current = requestAnimationFrame(measure);
    };

    const io = new IntersectionObserver(
      (entries) => {
        active.current = entries[0]?.isIntersecting ?? false;
        if (active.current) onScroll();
      },
      { threshold: 0 }
    );
    io.observe(el);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    measure();

    return () => {
      io.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, []);

  return [ref, p];
}

/** Counts to a target once triggered. Uses rAF, stops exactly on target. */
export function useCountUp(target: number, run: boolean, ms = 900, decimals = 0) {
  const [v, setV] = useState(0);

  useEffect(() => {
    if (!run) return;
    if (typeof window === 'undefined') return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setV(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      const eased = 1 - Math.pow(1 - k, 3);
      const next = target * eased;
      setV(decimals ? Number(next.toFixed(decimals)) : Math.round(next));
      if (k < 1) raf = requestAnimationFrame(tick);
      else setV(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, ms, decimals]);

  return v;
}

export function useCopy(): [boolean, (text: string) => void] {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number>();

  const copy = useCallback((text: string) => {
    const done = () => {
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1400);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(done);
    } else {
      done();
    }
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);
  return [copied, copy];
}

export function useMediaQuery(query: string): boolean {
  const [match, setMatch] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false
  );
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return match;
}
