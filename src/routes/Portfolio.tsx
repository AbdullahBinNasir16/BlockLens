import { useEffect, useMemo, useState } from 'react';
import { fetchFeed, type ForwardRecord } from '../lib/live/launches';
import type { Trade, TradeKind } from '../data/types';
import { BOOK_NOW, INCEPTION, PORTFOLIO_NOTE, START_CAPITAL, TRADES } from '../data/portfolio';
import {
  DAY,
  bookStats,
  byKind,
  heldDays,
  isOpen,
  isWin,
  multiple,
  tradePath,
  tradePnl,
  tradeReturn,
} from '../lib/portfolio';
import { compact, dateShort } from '../lib/format';
import { ProvChip, SectionHead } from '../components/primitives/Bits';
import { MiniRing } from '../components/primitives/Meters';
import { Sparkline } from '../components/primitives/Charts';
import { EquityChart } from '../components/portfolio/EquityChart';
import { GateField } from '../components/portfolio/GateField';
import { KIND_LABEL, KindTag, PairMark } from '../components/portfolio/PairMark';
import { TradeDossier } from '../components/portfolio/TradeDossier';

/* ============================================================
   Portfolio — the model's own book.

   Read top to bottom it answers four questions in order: how is it doing,
   how does it decide, what does it hold, and what has it done. Every
   trade on the page opens the same dossier, where the model says why.
   ============================================================ */

const signed = (v: number, digits = 0) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(digits)}`;
const usd = (v: number) => `${v >= 0 ? '+' : '−'}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`;

function firstSentence(s: string) {
  const i = s.search(/\.\s/);
  return i === -1 ? s : s.slice(0, i + 1);
}

/** The first sentence of the thesis, or for a memecoin the lore's hook —
 *  the line that says why in the fewest words. */
const why = (t: Trade) => (t.kind === 'meme' ? t.lore.hook : firstSentence(t.thesis[0]));

type Outcome = 'all' | 'won' | 'lost' | 'open';
type SortKey = 'date' | 'return' | 'size';

/* returns on a log scale, so a double and a halving draw the same length */
const MAX_LOG = Math.log2(6);
const barHalf = (t: Trade) => Math.min(1, Math.abs(Math.log2(multiple(t))) / MAX_LOG) * 50;

export function Portfolio() {
  const stats = useMemo(bookStats, []);
  const kinds = useMemo(byKind, []);
  const [open, setOpen] = useState<Trade | null>(null);

  const [kind, setKind] = useState<TradeKind | 'all'>('all');
  const [outcome, setOutcome] = useState<Outcome>('all');
  const [sort, setSort] = useState<SortKey>('date');

  const rows = useMemo(() => {
    const f = TRADES.filter(
      (t) =>
        (kind === 'all' || t.kind === kind) &&
        (outcome === 'all' ||
          (outcome === 'open' && isOpen(t)) ||
          (outcome === 'won' && isWin(t)) ||
          (outcome === 'lost' && !isOpen(t) && !isWin(t)))
    );
    const key = (t: Trade) => (sort === 'date' ? t.entryAt : sort === 'return' ? tradeReturn(t) : t.size);
    return f.sort((a, b) => key(b) - key(a));
  }, [kind, outcome, sort]);

  const positions = TRADES.filter(isOpen).sort((a, b) => b.entryAt - a.entryAt);
  const maxKindPnl = Math.max(...kinds.map((k) => Math.abs(k.pnl)));
  const sinceLast = Math.round((BOOK_NOW - stats.lastEntry.entryAt) / DAY);
  const up = stats.ret >= 0;

  return (
    <div className="bl-page bl-pf">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Paper trading · Base</p>
          <h1 className="display d2">Portfolio</h1>
          <p className="bl-page__sub">
            BlockLens's paper agent trades its own signal on every new Base launch, by rules fixed
            before the first outcome, and reports what it earned. Below it is an illustrative
            simulation of how a book is meant to read. That part is not a record.
          </p>
        </div>
      </header>

      <RealAgent />

      <div className="bl-pf__simhead">
        <div>
          <p className="eyebrow">Illustrative simulation — not a record</p>
          <p className="meta">
            Invented trades, prices and stories, written to show how the book and its reasoning are
            meant to look. Some stories mention real companies and people; none of it happened.
            Last simulated buy {sinceLast}d before the simulation's own clock.
          </p>
        </div>
        <ProvChip live={false} note={PORTFOLIO_NOTE} />
      </div>

      {/* ---------------- performance ---------------- */}
      <section className="bl-pfhero" aria-label="Performance">
        <div className="bl-pfhero__main">
          <span className="eyebrow">Book value</span>
          <span className="bl-pfhero__v num">${Math.round(stats.value).toLocaleString('en-US')}</span>
          <span className="bl-pfhero__r num" data-up={up}>
            {signed(stats.ret * 100, 1)}%
            <span className="meta">
              {' '}
              on ${compact(START_CAPITAL)} since {dateShort(INCEPTION)}
            </span>
          </span>
          <dl className="bl-pfhero__split">
            <div>
              <dt className="meta">Realized</dt>
              <dd className="num" data-up={stats.realized >= 0}>
                {usd(stats.realized)}
              </dd>
            </div>
            <div>
              <dt className="meta">Unrealized</dt>
              <dd className="num" data-up={stats.unrealized >= 0}>
                {usd(stats.unrealized)}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bl-pfhero__win">
          <MiniRing value={stats.winRate * 100} color="var(--pos)" size={132} stroke={4.2}>
            <span className="bl-pfhero__wv num">{Math.round(stats.winRate * 100)}%</span>
          </MiniRing>
          <span className="bl-pfhero__wl">
            <span className="eyebrow eyebrow-ink">Win rate</span>
            <span className="meta">
              {stats.wins} of {stats.closed} closed trades
            </span>
          </span>
        </div>

        <dl className="bl-pfhero__stats">
          <div>
            <dt className="meta">Trades</dt>
            <dd className="num">{TRADES.length}</dd>
          </div>
          <div>
            <dt className="meta">Open</dt>
            <dd className="num">{stats.open}</dd>
          </div>
          <div>
            <dt className="meta">Avg hold</dt>
            <dd className="num">{Math.round(stats.avgHoldDays)}d</dd>
          </div>
          <div>
            <dt className="meta">Max drawdown</dt>
            <dd className="num" data-up="false">
              −{(stats.maxDrawdown * 100).toFixed(1)}%
            </dd>
          </div>
          <div>
            <dt className="meta">Best</dt>
            <dd className="num">
              <button className="bl-pflink" onClick={() => setOpen(stats.best)}>
                {stats.best.ticker} {signed(tradeReturn(stats.best) * 100)}%
              </button>
            </dd>
          </div>
          <div>
            <dt className="meta">Worst</dt>
            <dd className="num">
              <button className="bl-pflink" onClick={() => setOpen(stats.worst)}>
                {stats.worst.ticker} {signed(tradeReturn(stats.worst) * 100)}%
              </button>
            </dd>
          </div>
        </dl>

        <div className="bl-pfkinds">
          <span className="eyebrow">Where it made money</span>
          {kinds.map((k) => (
            <div key={k.kind} className="bl-pfkind">
              <span className="bl-pfkind__l">{KIND_LABEL[k.kind]}</span>
              <span className="bl-pfkind__bar" aria-hidden="true">
                <span
                  data-up={k.pnl >= 0}
                  style={{ width: `${(Math.abs(k.pnl) / maxKindPnl) * 100}%` }}
                />
              </span>
              <span className="bl-pfkind__v num" data-up={k.pnl >= 0}>
                {usd(k.pnl)}
              </span>
              <span className="bl-pfkind__w meta">
                {k.wins}/{k.closed} won
              </span>
            </div>
          ))}
        </div>
      </section>

      <EquityChart onSelect={setOpen} />

      {/* ---------------- the gate ---------------- */}
      <section className="bl-pfsec">
        <SectionHead
          index="01"
          title="The gate"
          sub="It only buys what clears every line. Most of what clears still isn’t bought."
        />
        <GateField onSelect={setOpen} />
      </section>

      {/* ---------------- open positions ---------------- */}
      <section className="bl-pfsec">
        <SectionHead
          index="02"
          title="Open positions"
          sub="What it holds right now, and what would make it sell."
        />
        <div className="bl-pos4">
          {positions.map((t) => {
            const r = tradeReturn(t);
            return (
              <button key={t.id} className="bl-opos" onClick={() => setOpen(t)}>
                <span className="bl-opos__top">
                  <PairMark trade={t} size="lg" />
                  <KindTag kind={t.kind} />
                </span>
                <span className="bl-opos__r num" data-up={r >= 0}>
                  {signed(r * 100)}%
                </span>
                <span className="bl-opos__spark">
                  <Sparkline
                    values={tradePath(t)}
                    width={240}
                    height={46}
                    color={r >= 0 ? 'var(--pos)' : 'var(--neg)'}
                  />
                </span>
                <span className="bl-opos__meta meta">
                  {usd(tradePnl(t))} · ${compact(t.size)} · held {Math.round(heldDays(t))}d
                </span>
                <span className="bl-opos__why">{why(t)}</span>
                <span className="bl-opos__watch">
                  <span className="eyebrow">Watching</span>
                  {t.exitNote}
                </span>
                <span className="bl-opos__cta meta">Read the thesis →</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ---------------- history ---------------- */}
      <section className="bl-pfsec">
        <SectionHead
          index="03"
          title="Trade history"
          sub="Every trade the model has made, with the line that says why. Open any one to read the full thesis."
        />

        <div className="bl-hbar">
          <div className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Kind">
            {(['all', 'meme', 'ai', 'infra', 'defi'] as const).map((k) => (
              <button
                key={k}
                role="radio"
                aria-checked={kind === k}
                className="bl-seg__b"
                data-on={kind === k}
                onClick={() => setKind(k)}
              >
                {k === 'all' ? 'All' : KIND_LABEL[k]}
              </button>
            ))}
          </div>
          <div className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Outcome">
            {(['all', 'won', 'lost', 'open'] as Outcome[]).map((o) => (
              <button
                key={o}
                role="radio"
                aria-checked={outcome === o}
                className="bl-seg__b"
                data-on={outcome === o}
                onClick={() => setOutcome(o)}
              >
                {o === 'all' ? 'Any outcome' : o[0].toUpperCase() + o.slice(1)}
              </button>
            ))}
          </div>
          <div className="bl-hbar__sort">
            <span className="meta">Sort</span>
            <div className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Sort">
              {(['date', 'return', 'size'] as SortKey[]).map((s) => (
                <button
                  key={s}
                  role="radio"
                  aria-checked={sort === s}
                  className="bl-seg__b"
                  data-on={sort === s}
                  onClick={() => setSort(s)}
                >
                  {s === 'date' ? 'Newest' : s === 'return' ? 'Return' : 'Size'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {rows.length === 0 ? (
          <p className="bl-hempty meta">No trades match — try another kind or outcome.</p>
        ) : (
          <ol className="bl-pfhist">
            {rows.map((t) => {
              const r = tradeReturn(t);
              const state = isOpen(t) ? 'open' : isWin(t) ? 'won' : 'lost';
              return (
                <li key={t.id}>
                  <button className="bl-hrow" onClick={() => setOpen(t)}>
                    <span className="bl-hrow__d num">{dateShort(t.entryAt).slice(0, 6)}</span>
                    <span className="bl-hrow__pair">
                      <PairMark trade={t} size="md" />
                      <KindTag kind={t.kind} />
                    </span>
                    <span className="bl-hrow__why" data-lore={t.kind === 'meme'}>
                      {why(t)}
                    </span>
                    <span className="bl-hrow__held meta">{Math.max(1, Math.round(heldDays(t)))}d</span>
                    <span className="bl-hrow__bar" aria-hidden="true">
                      <span
                        className="bl-hrow__fill"
                        data-up={r >= 0}
                        style={r >= 0 ? { left: '50%', width: `${barHalf(t)}%` } : { right: '50%', width: `${barHalf(t)}%` }}
                      />
                    </span>
                    <span className="bl-hrow__r num" data-up={r >= 0}>
                      {signed(r * 100)}%
                    </span>
                    <span className="bl-hrow__pnl num">{usd(tradePnl(t))}</span>
                    <span className="bl-hrow__s" data-state={state}>
                      {state}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        )}

        <p className="bl-page__foot meta">{PORTFOLIO_NOTE}</p>
      </section>

      <TradeDossier trade={open} onClose={() => setOpen(null)} />
    </div>
  );
}

/* ============================================================
   The real paper agent — pre-registered (DECISIONS.md, Phase 9).
   ============================================================ */

function RealAgent() {
  const [f, setF] = useState<ForwardRecord | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetchFeed()
        .then((d) => alive && (setF(d.forward), setErr('')))
        .catch((e) => alive && setErr(String(e?.message ?? e)));
    load();
    const t = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const pol = f?.paper_agent?.policies;
  const head = pol?.headline;
  const ready = !!head?.reportable;
  const pct = (x?: number) => (x == null ? '—' : `${x > 0 ? '+' : ''}${(x * 100).toFixed(1)}%`);
  const rows: [string, string][] = [
    ['AGENT', 'Buys only launchpad launches scored under 20% risk'],
    ['CONTROL', 'Buys every scored launch'],
    ['AVOIDED', 'The launches the agent refused'],
    ['LAUNCHPAD', 'Post-hoc check: every launchpad launch, no risk score'],
  ];
  const ci = head?.agent_minus_control_ci as [number, number] | undefined;
  const lp = head?.agent_minus_launchpad_ci as [number, number] | undefined;
  const capped = head?.AGENT?.capped ?? 0;

  return (
    <section className="bl-pfsec bl-pf__real">
      <div className="bl-unres__sech">
        <h2 className="eyebrow">The paper agent · forward record</h2>
        <span className="bl-live__state" data-status={err ? 'error' : f ? 'live' : 'loading'}>
          <span className="bl-live__dot" />
          {err ? 'API not running' : f ? 'Live · paper only' : 'Connecting'}
        </span>
      </div>
      <ul className="bl-launch__val meta" style={{ marginBottom: 16 }}>
        <li>Buys at launch + 5 minutes at that price, sells at hour 6. One unit per trade, 3% round-trip cost.</li>
        <li>If the liquidity was pulled before the exit, the trade counts as a total loss. Gains are capped at +1,000%.</li>
        <li>
          Success means beating buy-everything, with the interval above zero. No conclusion before{' '}
          {f?.paper_agent?.floor ?? 100} agent trades.
        </li>
      </ul>
      {err && (
        <p className="meta">
          The record lives in the BlockLens API, which is not answering ({err}). Start it with
          backend/scripts/start_live.ps1.
        </p>
      )}
      {head && (
        <div className="bl-tablewrap">
          <table className="bl-table">
            <thead>
              <tr>
                <th>Policy</th>
                <th className="bl-th--r">Trades</th>
                <th className="bl-th--r">Mean</th>
                <th className="bl-th--r">Median</th>
                <th className="bl-th--r">Hit rate</th>
                <th className="bl-th--r">At 1% / 10% cost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([k, desc]) => {
                const r = head[k] ?? { trades: 0 };
                return (
                  <tr key={k}>
                    <td>
                      <span className="bl-tokencell__b">
                        <span className="bl-tokencell__n">{k}</span>
                        <span className="bl-tokencell__t meta">{desc}</span>
                      </span>
                    </td>
                    <td className="bl-td--r num">{r.trades}</td>
                    <td className="bl-td--r num">{ready ? pct(r.mean) : '—'}</td>
                    <td className="bl-td--r num">{ready ? pct(r.median) : '—'}</td>
                    <td className="bl-td--r num">{ready && r.hit_rate != null ? `${Math.round(r.hit_rate * 100)}%` : '—'}</td>
                    <td className="bl-td--r num">
                      {ready ? `${pct(pol?.low?.[k]?.mean)} / ${pct(pol?.high?.[k]?.mean)}` : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {!ready && (
        <p className="meta" style={{ marginTop: 12 }}>
          Too early: returns are hidden until the pre-registered floor is reached, so an early lucky or
          unlucky streak cannot be read as a result.
        </p>
      )}
      {ready && ci && (
        <ul className="bl-launch__val meta" style={{ marginTop: 12 }}>
          <li>
            Agent minus buy-everything, 95% interval: {pct(ci[0])} to {pct(ci[1])}.{' '}
            {ci[0] > 0
              ? 'It beats the control, which is the pre-registered test.'
              : 'Not beating the control; reported as it stands.'}
          </li>
          {lp && (
            <li>
              Post-hoc check, agent minus launchpad-only: {pct(lp[0])} to {pct(lp[1])}.{' '}
              {lp[0] > 0
                ? 'The risk score adds to the launch-type filter.'
                : 'The interval includes zero: the edge comes from avoiding self-deployed launches, not from the risk score.'}
            </li>
          )}
          <li>
            The median trade is {pct(head?.AGENT?.median)}. {capped} of {head?.AGENT?.trades} agent trades
            hit the +1,000% cap.{' '}
            {(head?.AGENT?.median ?? 0) <= 0 &&
              'The typical trade loses about the cost; any positive mean comes from those few large winners. The agent avoids losses more than it picks winners.'}
          </li>
        </ul>
      )}
    </section>
  );
}
