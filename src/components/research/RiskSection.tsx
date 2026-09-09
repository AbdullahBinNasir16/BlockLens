import { useState } from 'react';
import { useProject } from '../../lib/project-context';
import { Section } from './Section';
import { bandColor } from '../../lib/format';

/* ============================================================
   Risk reads as one picture: every signal placed on a single
   0-100 scale, so the spread and the outliers are visible before
   any label is read. Hover a marker to see which one it is.
   ============================================================ */

export function RiskSection() {
  const { risks } = useProject();
  const [hot, setHot] = useState<string | null>(null);

  const ranked = [...risks].sort((a, b) => b.score - a.score);
  const active = ranked.find((r) => r.id === hot) ?? ranked[0];

  const counts = {
    low: risks.filter((r) => r.level === 'low').length,
    medium: risks.filter((r) => r.level === 'medium').length,
    high: risks.filter((r) => r.level === 'high').length,
  };

  return (
    <Section
      id="risk"
      index="10"
      title="Risk Analysis"
      sub="Every signal on one scale. Further right is more concerning."
      right={
        <span className="bl-riskcounts">
          <span style={{ color: 'var(--pos)' }}>{counts.low} low</span>
          <span style={{ color: 'var(--warn)' }}>{counts.medium} med</span>
          <span style={{ color: 'var(--neg)' }}>{counts.high} high</span>
        </span>
      }
      wide
    >
      {(seen) => (
        <div className="bl-riskwrap">
          {/* ---------------- the spectrum ---------------- */}
          <div className="bl-spectrum" onMouseLeave={() => setHot(null)}>
            <div className="bl-spectrum__bands" aria-hidden="true">
              <span style={{ flexBasis: '40%', background: 'var(--pos-soft)' }} />
              <span style={{ flexBasis: '25%', background: 'var(--warn-soft)' }} />
              <span style={{ flexBasis: '35%', background: 'var(--neg-soft)' }} />
            </div>

            <div className="bl-spectrum__track">
              {ranked.map((r, i) => (
                <button
                  key={r.id}
                  className="bl-spectrum__pin"
                  data-on={active?.id === r.id}
                  style={{
                    left: `${r.score}%`,
                    borderColor: bandColor[r.level],
                    background: active?.id === r.id ? bandColor[r.level] : 'var(--paper)',
                    transform: seen
                      ? 'translate(-50%, -50%) scale(1)'
                      : 'translate(-50%, -50%) scale(0)',
                    transitionDelay: `${i * 60}ms`,
                  }}
                  onMouseEnter={() => setHot(r.id)}
                  onFocus={() => setHot(r.id)}
                  aria-label={`${r.label}, ${r.score} of 100`}
                >
                  <span className="num">{r.score}</span>
                </button>
              ))}
            </div>

            <div className="bl-spectrum__axis">
              <span className="meta" style={{ color: 'var(--pos)' }}>
                Low
              </span>
              <span className="meta" style={{ color: 'var(--warn)' }}>
                Medium
              </span>
              <span className="meta" style={{ color: 'var(--neg)' }}>
                High
              </span>
            </div>
          </div>

          {/* ---------------- readout for the hovered pin ---------------- */}
          {active && (
            <div className="bl-riskread" style={{ borderColor: bandColor[active.level] }}>
              <span className="eyebrow" style={{ color: bandColor[active.level] }}>
                {active.level} · {active.score} / 100
              </span>
              <p className="bl-riskread__l">{active.label}</p>
              <p className="bl-riskread__s">{active.summary}</p>
            </div>
          )}

          {/* ---------------- compact ranked list ---------------- */}
          <ul className="bl-risklist">
            {ranked.map((r) => (
              <li
                key={r.id}
                className="bl-riskrow"
                data-on={active?.id === r.id}
                onMouseEnter={() => setHot(r.id)}
                onMouseLeave={() => setHot(null)}
              >
                <span className="bl-riskrow__dot" style={{ background: bandColor[r.level] }} />
                <span className="bl-riskrow__l">{r.label}</span>
                <span className="bl-riskrow__track">
                  <span
                    className="bl-riskrow__fill"
                    style={{
                      width: seen ? `${r.score}%` : 0,
                      background: bandColor[r.level],
                    }}
                  />
                </span>
                <span className="bl-riskrow__v num" style={{ color: bandColor[r.level] }}>
                  {r.score}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  );
}
