import { useState } from 'react';
import type { Trade } from '../../data/types';
import { CANDIDATES, GATE, RISK_TIGHTENED_AT, RULE_LOG, TRADES } from '../../data/portfolio';
import { isOpen, isWin, tradeReturn } from '../../lib/portfolio';
import { compact, dateShort, int } from '../../lib/format';

/* ============================================================
   How the model decides.

   On the left, the rule. On the right, every launch it scored this year,
   placed by risk and confidence — so the rule is seen doing its work: a
   dust of launches everywhere, a shaded corner where the rule says yes,
   and inside the corner, the few it actually bought. Most of what clears
   the scores is still passed over, and the reasons are counted.
   ============================================================ */

const W = 520;
const H = 400;
const PAD = { l: 40, r: 14, t: 14, b: 36 };
const x = (risk: number) => PAD.l + (risk / 100) * (W - PAD.l - PAD.r);
const y = (conf: number) => PAD.t + (1 - conf / 100) * (H - PAD.t - PAD.b);

const REASON: Record<string, string> = {
  liquidity: 'thin liquidity',
  lore: 'weak lore',
  age: 'too old by the time it scored',
  capacity: 'book already full',
};

const tone = (t: Trade) => (isOpen(t) ? 'open' : isWin(t) ? 'win' : 'loss');

export function GateField({ onSelect }: { onSelect: (t: Trade) => void }) {
  const [hot, setHot] = useState<string | null>(null);

  const passed = CANDIDATES.filter((c) => c.passedOver);
  const reasons = Object.entries(
    passed.reduce<Record<string, number>>((a, c) => {
      a[c.passedOver!] = (a[c.passedOver!] ?? 0) + 1;
      return a;
    }, {})
  ).sort((a, b) => b[1] - a[1]);

  const scored = CANDIDATES.length + TRADES.length;
  const cleared = passed.length + TRADES.length;
  const active = TRADES.find((t) => t.id === hot) ?? null;

  const rules = [
    { k: 'Age at entry', v: `≤ ${GATE.maxAgeHours}h` },
    { k: 'Confidence', v: `≥ ${GATE.minConfidence}` },
    {
      k: 'Risk',
      v: `≤ ${GATE.maxRisk}`,
      note: `memecoins ≤ ${GATE.maxRiskMeme} since ${dateShort(RISK_TIGHTENED_AT).slice(0, 6)}`,
    },
    { k: 'Liquidity', v: `≥ $${compact(GATE.minLiquidity)}` },
    { k: 'Lore', v: `≥ ${GATE.minLore}`, note: 'memecoins only' },
  ];

  return (
    <div className="bl-gate">
      <div className="bl-gate__rule">
        <ol className="bl-gate__list">
          {rules.map((r) => (
            <li key={r.k} className="bl-gate__row">
              <span className="bl-gate__k">{r.k}</span>
              <span className="bl-gate__v num">{r.v}</span>
              {r.note && <span className="bl-gate__n meta">{r.note}</span>}
            </li>
          ))}
        </ol>

        <div className="bl-gate__funnel">
          {[
            { n: scored, l: 'launches scored' },
            { n: cleared, l: 'cleared the scores' },
            { n: TRADES.length, l: 'bought' },
          ].map((s, i) => (
            <div key={s.l} className="bl-gate__step">
              <span className="bl-gate__sn num">{int(s.n)}</span>
              <span className="bl-gate__sl">{s.l}</span>
              {/* the bar is the share of everything scored, so the narrowing reads at a glance */}
              <span className="bl-gate__sb" style={{ width: `${Math.max(1.5, (s.n / scored) * 100)}%` }} data-last={i === 2} />
            </div>
          ))}
        </div>

        <p className="bl-gate__why">
          {passed.length} cleared the scores and were still passed over —{' '}
          {reasons.map(([r, n], i) => (
            <span key={r}>
              {i > 0 && (i === reasons.length - 1 ? ', and ' : ', ')}
              <b className="num">{n}</b> {REASON[r]}
            </span>
          ))}
          .
        </p>

        <ol className="bl-gate__log">
          {RULE_LOG.map((r) => (
            <li key={r.at}>
              <span className="bl-gate__logd num">{dateShort(r.at)}</span>
              <span className="bl-gate__logt">{r.text}</span>
            </li>
          ))}
        </ol>
      </div>

      <figure className="bl-gate__field">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="bl-gate__svg"
          role="img"
          aria-label={`${scored} launches by risk and confidence; ${TRADES.length} bought`}
          onMouseLeave={() => setHot(null)}
        >
          {/* the corner the rule says yes to */}
          <rect
            x={x(0)}
            y={y(100)}
            width={x(GATE.maxRisk) - x(0)}
            height={y(GATE.minConfidence) - y(100)}
            className="bl-gate__corner"
          />
          <line x1={x(GATE.maxRisk)} x2={x(GATE.maxRisk)} y1={y(100)} y2={y(0)} className="bl-gate__lim" />
          <line x1={x(0)} x2={x(100)} y1={y(GATE.minConfidence)} y2={y(GATE.minConfidence)} className="bl-gate__lim" />
          <line
            x1={x(GATE.maxRiskMeme)}
            x2={x(GATE.maxRiskMeme)}
            y1={y(100)}
            y2={y(GATE.minConfidence)}
            className="bl-gate__lim bl-gate__lim--meme"
          />
          <text x={x(GATE.maxRisk) + 5} y={y(97)} className="bl-gate__liml">
            risk ≤ {GATE.maxRisk}
          </text>
          <text x={x(96)} y={y(GATE.minConfidence) - 6} textAnchor="end" className="bl-gate__liml">
            confidence ≥ {GATE.minConfidence}
          </text>

          {[0, 25, 50, 75, 100].map((v) => (
            <g key={v}>
              <text x={x(v)} y={H - PAD.b + 16} textAnchor="middle" className="bl-gate__tick">
                {v}
              </text>
              <text x={PAD.l - 8} y={y(v) + 3} textAnchor="end" className="bl-gate__tick">
                {v}
              </text>
            </g>
          ))}
          <text x={W - PAD.r} y={H - 4} textAnchor="end" className="bl-gate__axis">
            Risk →
          </text>
          <text x={11} y={y(0)} transform={`rotate(-90 11 ${y(0)})`} className="bl-gate__axis">
            Confidence →
          </text>

          {/* everything scored and not bought */}
          {CANDIDATES.map((c, i) => (
            <circle
              key={i}
              cx={x(c.risk)}
              cy={y(c.confidence)}
              r={c.passedOver ? 2.6 : 1.7}
              className={c.passedOver ? 'bl-gate__pass' : 'bl-gate__dust'}
            />
          ))}

          {/* the buys */}
          {TRADES.map((t) => (
            <g
              key={t.id}
              className="bl-gate__buy"
              data-tone={tone(t)}
              data-on={hot === t.id}
              onMouseEnter={() => setHot(t.id)}
              onClick={() => onSelect(t)}
              role="button"
              tabIndex={0}
              aria-label={`${t.ticker}: risk ${t.gate.risk}, confidence ${t.gate.confidence}`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(t);
                }
              }}
            >
              <circle cx={x(t.gate.risk)} cy={y(t.gate.confidence)} r={hot === t.id ? 7.5 : 5.5} />
              {hot === t.id && (
                <text x={x(t.gate.risk) + 11} y={y(t.gate.confidence) + 4} className="bl-gate__buyl">
                  {t.ticker}
                </text>
              )}
            </g>
          ))}
        </svg>

        <figcaption className="bl-gate__cap">
          {active ? (
            <>
              <b>{active.ticker}</b> — risk {active.gate.risk}, confidence {active.gate.confidence},{' '}
              <span data-up={tradeReturn(active) >= 0} className="num bl-gate__capr">
                {tradeReturn(active) >= 0 ? '+' : '−'}
                {Math.abs(tradeReturn(active) * 100).toFixed(0)}%
              </span>
              . Click to read why it bought.
            </>
          ) : (
            <>
              <span className="bl-gate__key" data-k="dust" /> scored, outside the rule
              <span className="bl-gate__key" data-k="pass" /> cleared, passed over
              <span className="bl-gate__key" data-k="win" /> bought — won
              <span className="bl-gate__key" data-k="loss" /> lost
              <span className="bl-gate__key" data-k="open" /> open
            </>
          )}
        </figcaption>
      </figure>
    </div>
  );
}
