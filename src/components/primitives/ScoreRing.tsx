import { useCountUp } from '../../lib/hooks';

interface Props {
  value: number;
  max?: number;
  label: string;
  caption?: string;
  color: string;
  size?: number;
  run: boolean;
  /** delay the sweep so stacked rings cascade */
  delay?: number;
}

/** Large circular score. One SVG, two animated properties, no library. */
export function ScoreRing({
  value,
  max = 100,
  label,
  caption,
  color,
  size = 208,
  run,
  delay = 0,
}: Props) {
  const R = 78;
  const C = 2 * Math.PI * R;
  const frac = Math.max(0, Math.min(1, value / max));
  const shown = useCountUp(value, run, 1000);

  /* 60 perimeter ticks — the technical register of an instrument dial */
  const ticks = Array.from({ length: 60 }, (_, i) => i);

  return (
    <figure className="bl-ring" style={{ width: size }}>
      <svg viewBox="0 0 200 200" width={size} height={size} aria-hidden="true">
        <g className="bl-ring__ticks">
          {ticks.map((i) => {
            const a = (i / 60) * 360;
            const major = i % 5 === 0;
            const lit = i / 60 <= frac;
            return (
              <line
                key={i}
                x1="100"
                y1={major ? 6 : 8}
                x2="100"
                y2={major ? 13 : 12}
                stroke={lit && run ? color : 'var(--rule-strong)'}
                strokeWidth={major ? 1.4 : 0.9}
                opacity={lit && run ? 0.9 : 0.5}
                transform={`rotate(${a} 100 100)`}
                style={{
                  transition: `stroke 420ms var(--ease) ${delay + (i / 60) * 700}ms, opacity 420ms var(--ease) ${
                    delay + (i / 60) * 700
                  }ms`,
                }}
              />
            );
          })}
        </g>

        <circle cx="100" cy="100" r={R} fill="none" stroke="var(--rule)" strokeWidth="9" />
        <circle
          cx="100"
          cy="100"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={run ? C * (1 - frac) : C}
          transform="rotate(-90 100 100)"
          style={{
            transition: `stroke-dashoffset 1100ms var(--ease) ${delay}ms`,
          }}
        />
      </svg>

      <figcaption className="bl-ring__center">
        <span className="bl-ring__value num">{shown}</span>
        <span className="bl-ring__max num">/ {max}</span>
        <span className="bl-ring__label eyebrow">{label}</span>
        {caption && <span className="bl-ring__caption meta">{caption}</span>}
      </figcaption>
    </figure>
  );
}
