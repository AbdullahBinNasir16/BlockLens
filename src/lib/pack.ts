/* Deterministic circle packing — a golden-angle spiral with collision
   push-back. No simulation loop, so it costs nothing per frame and the
   same input always lands in the same place. Shared by the holder field
   and the screener's wallet bubbles. */

export interface Circle {
  x: number;
  y: number;
  r: number;
}

export interface SpiralOptions {
  cx: number;
  cy: number;
  /** radial distance per step along the spiral */
  step: number;
  /** horizontal stretch, so the field fills a landscape frame */
  stretch: number;
  /** minimum gap between circles */
  gap: number;
  /** how far to move outward per collision retry */
  push: number;
}

/** Places circles in the order given — the first lands at the centre. */
export function spiralPack(radii: number[], o: SpiralOptions): Circle[] {
  const placed: Circle[] = [];

  radii.forEach((r, i) => {
    const a = i * 2.399963;
    let d = i === 0 ? 0 : o.step * Math.sqrt(i);
    let x = o.cx + Math.cos(a) * d * o.stretch;
    let y = o.cy + Math.sin(a) * d;

    /* push out along the same bearing until it clears everything placed */
    for (let guard = 0; guard < 400; guard++) {
      const hit = placed.some((p) => Math.hypot(p.x - x, p.y - y) < p.r + r + o.gap);
      if (!hit) break;
      d += o.push;
      x = o.cx + Math.cos(a) * d * o.stretch;
      y = o.cy + Math.sin(a) * d;
    }

    placed.push({ x, y, r });
  });

  return placed;
}

/** A viewBox cropped to what was actually placed, so a field fills its
 *  container instead of floating inside a fixed canvas. */
export function cropBox(circles: Circle[], pad: number): string {
  if (!circles.length) return '0 0 1 1';
  const x0 = Math.min(...circles.map((p) => p.x - p.r)) - pad;
  const x1 = Math.max(...circles.map((p) => p.x + p.r)) + pad;
  const y0 = Math.min(...circles.map((p) => p.y - p.r)) - pad;
  const y1 = Math.max(...circles.map((p) => p.y + p.r)) + pad;
  return `${x0} ${y0} ${x1 - x0} ${y1 - y0}`;
}
