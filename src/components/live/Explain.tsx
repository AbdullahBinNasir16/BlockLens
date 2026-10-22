import type { Explanation } from '../../lib/live/launches';

/* ============================================================
   The anatomy of one score.

   A base rate, then one bar per driver: left (green) lowers the risk,
   right (red) raises it, in log-odds. The bars are the model's own exact
   decomposition (backend/blocklens/live/explain.py), so what is shown is
   what the model did, not a story about it.
   ============================================================ */

const pct = (p: number) => `${Math.round(p * 100)}%`;

export function Explain({ why, compact = false }: { why: Explanation; compact?: boolean }) {
  const max = Math.max(0.01, ...why.drivers.map((d) => Math.abs(d.contribution)), Math.abs(why.rest));
  const bar = (c: number) => `${Math.min(50, (Math.abs(c) / max) * 50)}%`;
  return (
    <div className="bl-why" data-compact={compact}>
      <div className="bl-why__head">
        <span className="meta">
          Base rate <b className="num">{pct(why.base_rate)}</b>
        </span>
        <span className="bl-why__arrow" aria-hidden="true">
          →
        </span>
        <span className="meta">
          This launch <b className="num">{pct(why.risk)}</b>
        </span>
      </div>
      <ul className="bl-why__list">
        {why.drivers.map((d) => (
          <li key={d.feature} className="bl-why__row" data-dir={d.direction}>
            <span className="bl-why__label">
              {d.label}
              <span className="bl-why__val num">{d.display}</span>
            </span>
            <span className="bl-why__track" aria-hidden="true">
              <span className="bl-why__mid" />
              <span
                className="bl-why__bar"
                style={
                  d.contribution >= 0
                    ? { left: '50%', width: bar(d.contribution) }
                    : { right: '50%', width: bar(d.contribution) }
                }
              />
            </span>
            <span className="bl-why__c num" title={`${d.contribution.toFixed(3)} log-odds`}>
              {d.contribution > 0 ? '+' : ''}
              {d.contribution.toFixed(2)}
            </span>
          </li>
        ))}
        {Math.abs(why.rest) > 0.005 && (
          <li className="bl-why__row" data-dir={why.rest > 0 ? 'raises' : 'lowers'} data-rest="true">
            <span className="bl-why__label">everything else, together</span>
            <span className="bl-why__track" aria-hidden="true">
              <span className="bl-why__mid" />
              <span
                className="bl-why__bar"
                style={why.rest >= 0 ? { left: '50%', width: bar(why.rest) } : { right: '50%', width: bar(why.rest) }}
              />
            </span>
            <span className="bl-why__c num">
              {why.rest > 0 ? '+' : ''}
              {why.rest.toFixed(2)}
            </span>
          </li>
        )}
      </ul>
      {!compact && (
        <p className="meta bl-why__foot">
          Bars are the model's exact per-feature terms in log-odds (tree SHAP); they add up to the score. They
          say what moved the model's estimate, not what caused the launch to behave as it did.
        </p>
      )}
    </div>
  );
}
