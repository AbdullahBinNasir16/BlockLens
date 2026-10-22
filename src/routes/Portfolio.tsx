import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/app/Icons';
import { EmptyNote, Stat } from '../components/primitives/Bits';
import { bandColor, shortAddr, int } from '../lib/format';
import { fetchFeed, riskBand, type ForwardRecord } from '../lib/live/launches';
import {
  POLICY_LABEL,
  POLICY_RULE,
  equityCurve,
  fetchPaperBook,
  picks,
  policyStats,
  withoutCapped,
  type PaperBook,
  type PaperTrade,
  type Policy,
} from '../lib/live/paper';

/* ============================================================
   Paper Agent — the pre-registered forward record, trade by trade.

   Nothing here is simulated. Every row is a launch the live feed scored
   at minute 5 and resolved at hour 6, and every number on the page is
   derived from those rows in lib/live/paper.ts. The protocol, the
   policies and the cost were fixed before the first outcome existed
   (DECISIONS.md, Phase 9).
   ============================================================ */

type Load<T> = { state: 'loading' } | { state: 'ok'; value: T } | { state: 'error'; msg: string };
type Filter = 'AGENT' | 'AVOIDED' | 'ALL';

const pct = (x: number | undefined | null, digits = 1) =>
  x == null ? '—' : `${x > 0 ? '+' : ''}${(x * 100).toFixed(digits)}%`;

function when(iso: string): string {
  const d = new Date(iso);
  return `${d.toISOString().slice(5, 10)} ${d.toISOString().slice(11, 16)}`;
}

export function Portfolio() {
  const nav = useNavigate();
  const [book, setBook] = useState<Load<PaperBook>>({ state: 'loading' });
  const [forward, setForward] = useState<ForwardRecord | null>(null);
  const [filter, setFilter] = useState<Filter>('AGENT');
  const [sort, setSort] = useState<'time' | 'return' | 'risk'>('time');

  useEffect(() => {
    let alive = true;
    fetchPaperBook()
      .then((b) => alive && setBook({ state: 'ok', value: b }))
      .catch((e) => alive && setBook({ state: 'error', msg: String(e?.message ?? e) }));
    fetchFeed()
      .then((f) => alive && setForward(f.forward))
      .catch(() => alive && setForward(null));
    return () => {
      alive = false;
    };
  }, []);

  const trades = book.state === 'ok' ? book.value.trades : [];
  const stats = useMemo(
    () => ({
      AGENT: policyStats(trades, 'AGENT'),
      CONTROL: policyStats(trades, 'CONTROL'),
      LAUNCHPAD: policyStats(trades, 'LAUNCHPAD'),
      AVOIDED: policyStats(trades, 'AVOIDED'),
    }),
    [trades]
  );
  const uncapped = useMemo(() => policyStats(withoutCapped(trades), 'AGENT'), [trades]);
  const curves = useMemo(
    () => ({ AGENT: equityCurve(trades, 'AGENT'), CONTROL: equityCurve(trades, 'CONTROL') }),
    [trades]
  );
  const rows = useMemo(() => {
    const r = trades.filter((t) => (filter === 'ALL' ? true : picks(t, filter)));
    if (sort === 'return') r.sort((a, b) => (b.return ?? -9) - (a.return ?? -9));
    else if (sort === 'risk') r.sort((a, b) => (a.risk ?? 9) - (b.risk ?? 9));
    return r;
  }, [trades, filter, sort]);

  const pa = forward?.paper_agent;
  const headline = pa?.policies?.headline;
  const reportable = !!headline?.reportable;
  const a = stats.AGENT;
  const c = stats.CONTROL;

  return (
    <div className="bl-page bl-paper">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Forward record · Base · Live</p>
          <h1 className="display d2">Paper Agent</h1>
          <p className="bl-page__sub">
            BlockLens puts its own signal on the line. The agent buys a launch at minute 5 only when it is a
            launchpad launch with buyer-loss risk under {book.state === 'ok' ? `${Math.round(book.value.max_risk * 100)}%` : '20%'},
            sells at hour 6, and pays {book.state === 'ok' ? `${Math.round(book.value.cost * 100)}%` : '3%'} per round trip. Rules fixed before the first outcome.
          </p>
        </div>
        <div className="bl-page__headr bl-live">
          <span className="bl-live__state" data-status={book.state === 'ok' ? 'live' : book.state === 'error' ? 'error' : 'loading'}>
            <span className="bl-live__dot" />
            {book.state === 'ok' ? 'Live' : book.state === 'error' ? 'API unreachable' : 'Loading'}
          </span>
          {a && <span className="meta num">{int(a.trades)} agent trades</span>}
        </div>
      </header>

      {book.state === 'error' && (
        <EmptyNote
          title="The BlockLens API is not answering"
          detail={`${book.msg}. Start it with: uvicorn blocklens.api.app:app --port 8000`}
        />
      )}

      {book.state === 'ok' && !a && (
        <EmptyNote
          title="No resolved trades yet"
          detail="A trade resolves six hours after its launch. The agent's floor is 100 trades before anything is called a result."
        />
      )}

      {a && c && (
        <>
          <section className="bl-paper__hero">
            <Stat
              label="Agent mean return"
              value={pct(a.mean)}
              sub={`median ${pct(a.median)} · hit rate ${Math.round(a.hitRate * 100)}% · after costs`}
              tone={a.mean >= 0 ? 'var(--pos)' : 'var(--neg)'}
            />
            <Stat
              label="Buy-everything control"
              value={pct(c.mean)}
              sub={`${int(c.trades)} trades · ${int(c.pulled)} had liquidity pulled`}
              tone={c.mean >= 0 ? 'var(--pos)' : 'var(--neg)'}
            />
            <Stat
              label="Agent − control"
              value={headline?.agent_minus_control_ci ? `${pct(headline.agent_minus_control_ci[0], 0)} to ${pct(headline.agent_minus_control_ci[1], 0)}` : '—'}
              sub={reportable ? '95% bootstrap interval · pre-registered test' : `too early · floor ${pa?.floor ?? 100} trades`}
              tone={headline?.agent_minus_control_ci && headline.agent_minus_control_ci[0] > 0 ? 'var(--pos)' : undefined}
            />
            <Stat
              label="Without the capped trades"
              value={pct(uncapped?.mean)}
              sub={`${int(a.capped)} trades hit the +${book.state === 'ok' ? Math.round(book.value.cap * 100) : 1000}% cap`}
            />
          </section>

          <section className="bl-paper__chart">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Cumulative return · one unit per trade</h2>
              <span className="meta">
                <span className="bl-paper__key" style={{ background: 'var(--ink)' }} /> agent ·{' '}
                <span className="bl-paper__key" style={{ background: 'var(--ink-4)' }} /> buy everything
              </span>
            </div>
            <Equity agent={curves.AGENT} control={curves.CONTROL} />
          </section>

          <section className="bl-paper__policies">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Four policies, same launches, same cost</h2>
              <span className="meta">computed from the rows below</span>
            </div>
            <div className="bl-tablewrap">
              <table className="bl-table">
                <thead>
                  <tr>
                    <th>Policy</th>
                    <th>Rule</th>
                    <th className="bl-th--r">Trades</th>
                    <th className="bl-th--r">Mean</th>
                    <th className="bl-th--r">Median</th>
                    <th className="bl-th--r">Hit rate</th>
                    <th className="bl-th--r">Pulled</th>
                  </tr>
                </thead>
                <tbody>
                  {(['AGENT', 'LAUNCHPAD', 'CONTROL', 'AVOIDED'] as Policy[]).map((p) => {
                    const s = stats[p];
                    return (
                      <tr key={p}>
                        <td>
                          <b>{POLICY_LABEL[p]}</b>
                        </td>
                        <td className="meta">{POLICY_RULE[p]}</td>
                        <td className="bl-td--r num">{s ? int(s.trades) : '—'}</td>
                        <td className="bl-td--r num" style={s ? { color: s.mean >= 0 ? 'var(--pos)' : 'var(--neg)' } : undefined}>
                          {pct(s?.mean)}
                        </td>
                        <td className="bl-td--r num">{pct(s?.median)}</td>
                        <td className="bl-td--r num">{s ? `${Math.round(s.hitRate * 100)}%` : '—'}</td>
                        <td className="bl-td--r num">{s ? int(s.pulled) : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="bl-paper__note">
              <b>Where the edge comes from.</b> The agent beats buy-everything because self-deployed launches
              lose their liquidity; a model-free rule that buys every launchpad launch does about as well.
              {headline?.agent_minus_launchpad_ci && (
                <>
                  {' '}
                  Agent minus that rule: {pct(headline.agent_minus_launchpad_ci[0], 0)} to{' '}
                  {pct(headline.agent_minus_launchpad_ci[1], 0)}, an interval that spans zero (post hoc).
                </>
              )}{' '}
              The risk score has not yet been shown to add to the launch-type filter; the page says so rather
              than claiming it.
            </p>
          </section>

          <section className="bl-paper__trades">
            <div className="bl-filters">
              <div className="bl-filters__grp">
                <span className="eyebrow">Show</span>
                {(['AGENT', 'AVOIDED', 'ALL'] as Filter[]).map((f) => (
                  <button key={f} className="bl-fchip" data-on={filter === f} onClick={() => setFilter(f)}>
                    {f === 'AGENT' ? 'Agent bought' : f === 'AVOIDED' ? 'Agent refused' : 'Every scored launch'}
                  </button>
                ))}
              </div>
              <div className="bl-filters__grp">
                <span className="eyebrow">Sort</span>
                {(['time', 'return', 'risk'] as const).map((s) => (
                  <button key={s} className="bl-fchip" data-on={sort === s} onClick={() => setSort(s)}>
                    {s === 'time' ? 'Newest' : s === 'return' ? 'Return' : 'Risk'}
                  </button>
                ))}
              </div>
              <span className="meta num">{int(rows.length)} trades</span>
            </div>
            <div className="bl-tablewrap">
              <table className="bl-table bl-table--live">
                <thead>
                  <tr>
                    <th>Launched (UTC)</th>
                    <th>Token</th>
                    <th>Launch type</th>
                    <th className="bl-th--r">Risk</th>
                    <th className="bl-th--r">Price at 6h</th>
                    <th>Liquidity</th>
                    <th className="bl-th--r">Return</th>
                    <th>Agent</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 400).map((t) => (
                    <TradeRow key={t.token} t={t} onOpen={() => nav(`/app/token/${t.token}`)} />
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <p className="bl-page__foot meta">
        A paper record: no money moved. One unit of notional per trade, entry at the minute-5 price, exit at
        the hour-6 price, −100% when the pool's liquidity was gone by then, returns capped at +1,000% per
        trade. Only predictions scored before their outcome existed count. Protocol:{' '}
        {book.state === 'ok' ? book.value.protocol : 'DECISIONS.md, Phase 9'}.
      </p>
    </div>
  );
}

function TradeRow({ t, onOpen }: { t: PaperTrade; onOpen: () => void }) {
  const r = t.return;
  return (
    <tr className="bl-tr" onClick={onOpen}>
      <td className="meta num">{when(t.launch_ts)}</td>
      <td className="num">{shortAddr(t.token, 8, 6)}</td>
      <td>
        <span className="bl-tag" data-size="sm" data-tone={t.launch_type === 'self-deployed' ? 'negative' : undefined}>
          {t.launch_type === 'launchpad' ? 'Launchpad · locked' : 'Self-deployed'}
        </span>
      </td>
      <td className="bl-td--r num" style={t.risk != null ? { color: bandColor[riskBand(t.risk)] } : undefined}>
        {t.risk == null ? '—' : `${Math.round(t.risk * 100)}%`}
      </td>
      <td className="bl-td--r num">{t.price_6h_vs_cutoff == null ? '—' : `×${t.price_6h_vs_cutoff.toFixed(2)}`}</td>
      <td className="meta">{t.pulled ? <span style={{ color: 'var(--neg)' }}>pulled</span> : 'held'}</td>
      <td className="bl-td--r num" style={r != null ? { color: r >= 0 ? 'var(--pos)' : 'var(--neg)' } : undefined}>
        {pct(r, 0)}
        {t.capped ? <span className="meta"> cap</span> : ''}
      </td>
      <td className="meta">{t.agent ? <b>bought</b> : 'refused'}</td>
      <td className="bl-td--act">
        <span className="bl-rowacts">
          <a className="bl-iconbtn" href={`https://dexscreener.com/base/${t.pool}`} target="_blank" rel="noreferrer" title="Open on DexScreener" onClick={(e) => e.stopPropagation()}>
            <Icon.Ext size={13} />
          </a>
        </span>
      </td>
    </tr>
  );
}

/* Two cumulative-return lines on a shared trade axis, hand-built. */
function Equity({ agent, control }: { agent: { t: number; v: number }[]; control: { t: number; v: number }[] }) {
  const W = 900;
  const H = 220;
  const P = 28;
  const all = [...agent, ...control];
  if (all.length < 2) return <p className="meta">Not enough resolved trades to draw yet.</p>;
  const t0 = Math.min(...all.map((p) => p.t));
  const t1 = Math.max(...all.map((p) => p.t));
  const lo = Math.min(0, ...all.map((p) => p.v));
  const hi = Math.max(0, ...all.map((p) => p.v));
  const x = (t: number) => P + ((t - t0) / Math.max(1, t1 - t0)) * (W - P * 2);
  const y = (v: number) => P + (1 - (v - lo) / Math.max(1e-9, hi - lo)) * (H - P * 2);
  const path = (pts: { t: number; v: number }[]) =>
    pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join('');
  const ticks = [lo, 0, hi].filter((v, i, arr) => arr.indexOf(v) === i);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="bl-paper__svg" role="img" aria-label="Cumulative return of the agent against buy-everything">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={P} x2={W - P} y1={y(v)} y2={y(v)} stroke={v === 0 ? 'var(--rule-strong)' : 'var(--rule)'} strokeWidth="1" />
          <text x={W - P + 4} y={y(v) + 4} fontFamily="var(--mono)" fontSize="10" fill="var(--ink-4)">
            {v >= 0 ? '+' : ''}
            {v.toFixed(0)}
          </text>
        </g>
      ))}
      <path d={path(control)} fill="none" stroke="var(--ink-4)" strokeWidth="1.4" />
      <path d={path(agent)} fill="none" stroke="var(--ink)" strokeWidth="1.8" />
      <text x={P} y={H - 8} fontFamily="var(--mono)" fontSize="10" fill="var(--ink-4)">
        {new Date(t0).toISOString().slice(0, 10)}
      </text>
      <text x={W - P} y={H - 8} textAnchor="end" fontFamily="var(--mono)" fontSize="10" fill="var(--ink-4)">
        {new Date(t1).toISOString().slice(0, 10)}
      </text>
    </svg>
  );
}
