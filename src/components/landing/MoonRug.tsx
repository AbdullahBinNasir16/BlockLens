import { useMemo } from 'react';
import { useScrollProgress } from '../../lib/hooks';
import { linePath } from '../../lib/format';

const UP = [
  100, 118, 104, 132, 126, 158, 172, 150, 186, 204, 190, 232, 258, 240, 276, 302, 288, 330, 358,
  340, 384, 412, 396, 438, 460, 442, 478, 500, 486, 520,
];
const DOWN = [
  100, 128, 142, 120, 156, 138, 110, 92, 104, 78, 66, 72, 54, 46, 51, 38, 32, 35, 26, 22, 24, 18,
  15, 16, 12, 10, 11, 8, 7, 7,
];

const CW = 480;
const CH = 300;

/** map a value index to plate coordinates so reticles land on the line */
function pointAt(series: number[], i: number) {
  const min = Math.min(...series);
  const max = Math.max(...series);
  const span = max - min || 1;
  const x = 6 + (i / (series.length - 1)) * (CW - 12);
  const y = 6 + (1 - (series[i] - min) / span) * (CH - 12);
  return { x, y };
}

const FINDINGS_A = [
  { i: 7, text: 'KOL entry · day 2', dx: 14, dy: -30 },
  { i: 20, text: 'dev history verified', dx: -8, dy: -38 },
];
const FINDINGS_B = [
  { i: 5, text: 'wallet cluster forms', dx: 12, dy: -34 },
  { i: 13, text: 'liquidity thinned', dx: 16, dy: 34 },
];

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}
function stage(p: number, a: number, b: number) {
  return clamp01((p - a) / (b - a));
}

export function MoonRug() {
  const [ref, p] = useScrollProgress<HTMLDivElement>();

  const dUp = useMemo(() => linePath(UP, CW, CH, 6), []);
  const dDown = useMemo(() => linePath(DOWN, CW, CH, 6), []);

  const draw = stage(p, 0.04, 0.5);
  const outcome = stage(p, 0.42, 0.6);
  const line1 = stage(p, 0.55, 0.7);
  const line2 = stage(p, 0.78, 0.9);
  const findings = stage(p, 0.8, 0.96);

  /* copy cross-fades: line 1 leaves as line 2 arrives */
  const line1Out = 1 - stage(p, 0.76, 0.86);

  const headUp = pointAt(UP, Math.min(UP.length - 1, Math.round(draw * (UP.length - 1))));
  const headDown = pointAt(DOWN, Math.min(DOWN.length - 1, Math.round(draw * (DOWN.length - 1))));

  return (
    <section className="bl-mr" ref={ref}>
      <div className="bl-mr__sticky">
        <div className="bl-mr__inner">
          <p className="eyebrow bl-mr__eyebrow">Two contracts · deployed the same hour</p>

          <div className="bl-mr__charts">
            {/* ---------------- Project A ---------------- */}
            <figure className="bl-mr__fig">
              <figcaption className="bl-mr__cap">
                <span className="bl-mr__name">Project A</span>
                <span
                  className="bl-mr__result num"
                  style={{ color: 'var(--pos)', opacity: outcome }}
                >
                  +420%
                </span>
              </figcaption>

              <svg viewBox={`0 0 ${CW} ${CH}`} className="bl-mr__svg">
                <line x1="0" y1={CH - 6} x2={CW} y2={CH - 6} stroke="var(--rule)" strokeWidth="1" />
                <path
                  d={dUp}
                  fill="none"
                  stroke="var(--pos)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={1 - draw}
                />
                {draw > 0.02 && draw < 0.999 && (
                  <circle cx={headUp.x} cy={headUp.y} r="3.6" fill="var(--pos)" />
                )}

                {FINDINGS_A.map((f, k) => {
                  const pt = pointAt(UP, f.i);
                  const o = clamp01(findings * 2 - k * 0.5);
                  return (
                    <g key={k} opacity={o}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="9"
                        fill="none"
                        stroke="var(--ink)"
                        strokeWidth="1"
                      />
                      <line
                        x1={pt.x + (f.dx > 0 ? 9 : -9)}
                        y1={pt.y}
                        x2={pt.x + f.dx}
                        y2={pt.y + f.dy}
                        stroke="var(--ink-4)"
                        strokeWidth="0.9"
                      />
                      <text
                        x={pt.x + f.dx}
                        y={pt.y + f.dy - 6}
                        textAnchor={f.dx > 0 ? 'start' : 'end'}
                        fontFamily="var(--mono)"
                        fontSize="11"
                        letterSpacing="0.1em"
                        fill="var(--ink-2)"
                      >
                        {f.text.toUpperCase()}
                      </text>
                    </g>
                  );
                })}
              </svg>

              <div className="bl-mr__flag" style={{ opacity: outcome }}>
                <span className="bl-mr__flagdot" style={{ background: 'var(--pos)' }}>
                  ✓
                </span>
                <span className="meta">Signals held</span>
              </div>
            </figure>

            {/* ---------------- Project B ---------------- */}
            <figure className="bl-mr__fig">
              <figcaption className="bl-mr__cap">
                <span className="bl-mr__name">Project B</span>
                <span
                  className="bl-mr__result num"
                  style={{ color: 'var(--neg)', opacity: outcome }}
                >
                  −93%
                </span>
              </figcaption>

              <svg viewBox={`0 0 ${CW} ${CH}`} className="bl-mr__svg">
                <line x1="0" y1={CH - 6} x2={CW} y2={CH - 6} stroke="var(--rule)" strokeWidth="1" />
                <path
                  d={dDown}
                  fill="none"
                  stroke="var(--neg)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={1 - draw}
                />
                {draw > 0.02 && draw < 0.999 && (
                  <circle cx={headDown.x} cy={headDown.y} r="3.6" fill="var(--neg)" />
                )}

                {FINDINGS_B.map((f, k) => {
                  const pt = pointAt(DOWN, f.i);
                  const o = clamp01(findings * 2 - k * 0.5);
                  return (
                    <g key={k} opacity={o}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="9"
                        fill="none"
                        stroke="var(--ink)"
                        strokeWidth="1"
                      />
                      <line
                        x1={pt.x + 9}
                        y1={pt.y}
                        x2={pt.x + f.dx}
                        y2={pt.y + f.dy}
                        stroke="var(--ink-4)"
                        strokeWidth="0.9"
                      />
                      <text
                        x={pt.x + f.dx}
                        y={pt.y + f.dy + (f.dy > 0 ? 12 : -6)}
                        fontFamily="var(--mono)"
                        fontSize="11"
                        letterSpacing="0.1em"
                        fill="var(--ink-2)"
                      >
                        {f.text.toUpperCase()}
                      </text>
                    </g>
                  );
                })}
              </svg>

              <div className="bl-mr__flag" style={{ opacity: outcome }}>
                <span className="bl-mr__flagdot" style={{ background: 'var(--neg)' }}>
                  !
                </span>
                <span className="meta">Signals broke down</span>
              </div>
            </figure>
          </div>

          {/* ---------------- the two-beat line ---------------- */}
          <div className="bl-mr__copy">
            {/* the text sits in its own span: the <p> is a flex box, and a
                bare text node there would have its spaces collapsed away */}
            <p
              className="display d2 bl-mr__l1"
              style={{
                opacity: line1 * line1Out,
                transform: `translate3d(0,${(1 - line1) * 14}px,0)`,
              }}
            >
              <span>Every new project tells a different story.</span>
            </p>
            <p
              className="display d2 bl-mr__l2"
              style={{
                opacity: line2,
                transform: `translate3d(0,${(1 - line2) * 14}px,0)`,
              }}
            >
              <span>
                BlockLens investigates the story <em className="italic">behind</em> the chart.
              </span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
