import { useMemo } from 'react';
import type { AppliedCheck, ScreenerQuery, WalletMatch, WalletProjectPosition } from '../../data/types';
import { CHECK_BY_ID, QUANTIFIER_LABEL } from '../../data/checks';
import { datasets } from '../../data/projects';
import { CORPUS_NOW } from '../../data/wallets';
import {
  compare,
  holdingMinutes,
  projectCheckValue,
  quantifierHolds,
  realizedPnl,
  roiMultiple,
  scopedPositions,
  unrealizedPnl,
  walletCheckValue,
  type MetricCtx,
} from '../../lib/screener';
import { formatCheckValue, operatorLabel } from '../../lib/check-format';
import { compact, dateShort, duration, int, shortAddr, signedUsd } from '../../lib/format';
import { Drawer, KV, Tag } from '../primitives/Bits';
import { TokenMark } from '../primitives/TokenMark';
import { Icon } from '../app/Icons';
import { useCopy } from '../../lib/hooks';
import { DerivedRing } from './FilterChip';

/* ============================================================
   Why this wallet matched.

   Every check the query applied is restated here with the value it
   actually saw and whether that value passed. A wallet that appears in
   the table without an explanation is just an assertion — this panel is
   the difference between a screener and a list.
   ============================================================ */

/** The check library already names each funding source for its chip;
 *  reusing those labels keeps one vocabulary across the product. */
const FUNDING_LABEL: Record<string, string> = Object.fromEntries(
  (CHECK_BY_ID.fundingSource.options ?? []).map((o) => [o.value, o.label.toLowerCase()])
);

/* ---------------- cumulative realized PnL ---------------- */

function PnlLine({ positions, from, to }: { positions: WalletProjectPosition[]; from: number; to: number }) {
  const W = 440;
  const H = 132;
  const padL = 6;
  const padR = 6;
  const padT = 12;
  const padB = 20;

  const series = useMemo(() => {
    /* only closed positions move realized PnL, and they move it at the
       moment of the last sell — that is the whole event set */
    const events = positions
      .filter((p) => p.lastSell !== null)
      .map((p) => ({ t: p.lastSell as number, v: realizedPnl(p) }))
      .sort((a, b) => a.t - b.t);

    const end = Math.min(to, CORPUS_NOW);
    const pts: { t: number; v: number }[] = [{ t: from, v: 0 }];
    let run = 0;
    for (const e of events) {
      run += e.v;
      pts.push({ t: Math.max(from, Math.min(end, e.t)), v: run });
    }
    pts.push({ t: end, v: run });
    return pts;
  }, [positions, from, to]);

  const vals = series.map((p) => p.v);
  /* a little headroom so the peak never sits on the frame */
  const raw = Math.max(0, ...vals) - Math.min(0, ...vals);
  const pad = (raw || 1) * 0.14;
  const lo = Math.min(0, ...vals) - (Math.min(0, ...vals) < 0 ? pad : 0);
  const hi = Math.max(0, ...vals) + pad;
  const span = hi - lo || 1;
  const tSpan = Math.max(1, series[series.length - 1].t - series[0].t);

  const xAt = (t: number) => padL + ((t - series[0].t) / tSpan) * (W - padL - padR);
  const yAt = (v: number) => padT + (1 - (v - lo) / span) * (H - padT - padB);

  /* a step, not a curve: realized PnL does not drift between sells */
  let d = `M${xAt(series[0].t).toFixed(1)},${yAt(series[0].v).toFixed(1)}`;
  for (let i = 1; i < series.length; i++) {
    d += `H${xAt(series[i].t).toFixed(1)}V${yAt(series[i].v).toFixed(1)}`;
  }

  const zero = yAt(0);
  const final = vals[vals.length - 1];

  return (
    <figure className="bl-pnlline">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" role="img" aria-label="Cumulative realized PnL">
        <line x1={padL} y1={zero} x2={W - padR} y2={zero} stroke="var(--rule-strong)" strokeWidth="1" />
        <path
          d={`${d}V${zero}H${xAt(series[0].t).toFixed(1)}Z`}
          fill={final >= 0 ? 'var(--pos-soft)' : 'var(--neg-soft)'}
          opacity="0.75"
        />
        <path d={d} fill="none" stroke={final >= 0 ? 'var(--pos)' : 'var(--neg)'} strokeWidth="1.6" />
        {series.slice(1, -1).map((p, i) => (
          <circle key={i} cx={xAt(p.t)} cy={yAt(p.v)} r="2.6" fill="var(--paper)" stroke="var(--ink)" strokeWidth="1.1" />
        ))}
        <text x={padL} y={H - 6} className="bl-pnlline__t">
          {dateShort(series[0].t)}
        </text>
        <text x={W - padR} y={H - 6} textAnchor="end" className="bl-pnlline__t">
          {dateShort(series[series.length - 1].t)}
        </text>
        <text
          x={W - padR}
          y={Math.max(10, yAt(final) - 7)}
          textAnchor="end"
          className="bl-pnlline__v"
          fill={final >= 0 ? 'var(--pos)' : 'var(--neg)'}
        >
          {signedUsd(final)}
        </text>
      </svg>
      <figcaption className="meta">
        Cumulative realized PnL inside the window. Steps are exits; open positions are not counted
        until they close.
      </figcaption>
    </figure>
  );
}

/* ---------------- pass / fail mark ---------------- */

function Mark({ ok }: { ok: boolean }) {
  return (
    <span className="bl-passmark" data-ok={ok} title={ok ? 'Passed' : 'Failed'}>
      {ok ? '✓' : '×'}
    </span>
  );
}

/** The filter as its chip reads, so the drawer and the panel say the same
 *  thing in the same words. */
function checkLine(check: AppliedCheck) {
  const def = CHECK_BY_ID[check.checkId];
  const value = formatCheckValue(def, check.value);
  return def.valueType === 'boolean' ? value : `${operatorLabel(def, check.operator)} ${value}`;
}

function CheckName({ checkId }: { checkId: string }) {
  const def = CHECK_BY_ID[checkId];
  return (
    <span className="bl-cm__name">
      {def.derivation === 'derived' && <DerivedRing />}
      {def.label}
    </span>
  );
}

/* ---------------- panel ---------------- */

export function WalletDrawer({
  match,
  query,
  onClose,
}: {
  match: WalletMatch | null;
  query: ScreenerQuery;
  onClose: () => void;
}) {
  const [copied, copy] = useCopy();

  const positions = useMemo(
    () => (match ? scopedPositions(match.wallet, query) : []),
    [match, query]
  );

  if (!match) return null;
  const w = match.wallet;
  const ctx: MetricCtx = { from: query.scope.from, to: query.scope.to, now: CORPUS_NOW };

  const invested = positions.reduce((a, p) => a + p.invested, 0);
  const unrealized = positions.reduce((a, p) => a + unrealizedPnl(p), 0);
  const rule = query.projectRule;
  const projectIds = [...new Set(positions.map((p) => p.projectId))];
  const ruleHolds = quantifierHolds(rule.quantifier, match.matchedProjects.length, rule.count);

  return (
    <Drawer
      open
      onClose={onClose}
      eyebrow="Wallet"
      title={
        <span className="bl-wd__title num">
          {w.address.slice(0, 10)}…{w.address.slice(-8)}
          <button
            className="bl-addr__c"
            onClick={() => copy(w.address)}
            title={copied ? 'Copied' : 'Copy address'}
            aria-label="Copy address"
          >
            {copied ? <Icon.Check size={13} /> : <Icon.Copy size={13} />}
          </button>
        </span>
      }
      width={620}
    >
      <div className="bl-wd__tags">
        {w.ens && <Tag tone="ink">{w.ens}</Tag>}
        {w.label && <Tag>{w.label}</Tag>}
        {w.smartMoney && <Tag tone="positive">Smart money</Tag>}
        {w.insiderLinked && <Tag tone="negative">Insider-linked</Tag>}
        <Tag size="sm">Funded via {FUNDING_LABEL[w.fundingSource] ?? w.fundingSource}</Tag>
        {w.clusterSize > 1 && <Tag size="sm">Cluster of {w.clusterSize}</Tag>}
      </div>

      <div className="bl-wd__stats">
        <KV
          k="Realized PnL"
          v={signedUsd(match.realizedPnl)}
          tone={match.realizedPnl >= 0 ? 'var(--pos)' : 'var(--neg)'}
        />
        <KV
          k="Unrealized"
          v={signedUsd(unrealized)}
          tone={unrealized >= 0 ? 'var(--pos)' : 'var(--neg)'}
        />
        <KV k="Capital deployed" v={`$${compact(Math.round(invested))}`} />
        <KV k="Win rate" v={`${match.winRate.toFixed(0)}%`} />
        <KV k="Average hold" v={duration(match.avgHoldingTime)} />
        <KV k="First seen" v={dateShort(w.firstSeen)} />
        <KV k="Last active" v={dateShort(match.lastActive)} />
      </div>

      <PnlLine positions={positions} from={query.scope.from} to={query.scope.to} />

      {/* ---- positions ---- */}
      <h3 className="eyebrow eyebrow-ink bl-wd__sub">
        Positions in scope · {positions.length}
      </h3>
      <div className="bl-wd__positions">
        {positions.map((p) => {
          const project = datasets[p.projectId]?.project;
          const rp = realizedPnl(p);
          const roi = roiMultiple(p);
          return (
            <article className="bl-pos" key={p.projectId}>
              <header className="bl-pos__h">
                <span className="bl-pos__id">
                  {project && (
                    <TokenMark logo={project.logo} monogram={project.monogram} size={26} radius={8} />
                  )}
                  <span>
                    <span className="bl-pos__n">{project?.name ?? p.projectId}</span>
                    {project && (
                      <span className="bl-pos__ca num" title={project.contract}>
                        {shortAddr(project.contract, 6, 4)}
                      </span>
                    )}
                  </span>
                </span>
                <span
                  className="bl-pos__p num"
                  style={{ color: rp >= 0 ? 'var(--pos)' : 'var(--neg)' }}
                >
                  {signedUsd(rp)}
                </span>
              </header>

              <dl className="bl-pos__grid">
                <div>
                  <dt className="meta">Entry</dt>
                  <dd className="num">{dateShort(p.firstBuy)}</dd>
                </div>
                <div>
                  <dt className="meta">Exit</dt>
                  <dd className="num">{p.lastSell ? dateShort(p.lastSell) : 'Open'}</dd>
                </div>
                <div>
                  <dt className="meta">Held</dt>
                  <dd className="num">{duration(holdingMinutes(p, CORPUS_NOW))}</dd>
                </div>
                <div>
                  <dt className="meta">Invested</dt>
                  <dd className="num">${compact(p.invested)}</dd>
                </div>
                <div>
                  <dt className="meta">Sold</dt>
                  <dd className="num">{Math.round(p.soldFraction * 100)}%</dd>
                </div>
                <div>
                  <dt className="meta">ROI</dt>
                  <dd className="num">{roi.toFixed(2)}×</dd>
                </div>
                <div>
                  <dt className="meta">Trades</dt>
                  <dd className="num">
                    {p.buys}B / {p.sells}S
                  </dd>
                </div>
                <div>
                  <dt className="meta">Entry delay</dt>
                  <dd className="num">{duration(p.entryDelay / 60_000)}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>

      {/* ---- per-project filters ---- */}
      {rule.checks.length > 0 && (
        <section className="bl-wd__group">
          <h3 className="eyebrow eyebrow-ink bl-wd__sub">
            In each project · {QUANTIFIER_LABEL[rule.quantifier]} {rule.count}
          </h3>
          <p className="bl-wd__verdict" data-ok={ruleHolds}>
            <Mark ok={ruleHolds} />
            {match.matchedProjects.length} of {projectIds.length} projects passed every filter —{' '}
            {ruleHolds ? 'rule met' : 'rule not met'}
          </p>

          <div className="bl-tablewrap bl-tablewrap--inline">
            <table className="bl-minitable bl-checkmatrix">
              <thead>
                <tr>
                  <th>Filter</th>
                  {projectIds.map((id) => {
                    const p = datasets[id]?.project;
                    return (
                      <th key={id} className="bl-th--c" title={p?.name}>
                        {p?.ticker ?? id}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {rule.checks.map((chk) => {
                  const def = CHECK_BY_ID[chk.checkId];
                  return (
                    <tr key={chk.checkId}>
                      <td>
                        <CheckName checkId={chk.checkId} />
                        <span className="meta bl-cm__op">{checkLine(chk)}</span>
                      </td>
                      {projectIds.map((id) => {
                        const pos = positions.find((p) => p.projectId === id)!;
                        const v = projectCheckValue(chk, pos, w, ctx);
                        const ok = v !== undefined && compare(chk.operator, v, chk.value);
                        return (
                          <td key={id} className="bl-th--c bl-cm__cell" data-ok={ok}>
                            <span className="num">
                              {v === undefined ? '—' : formatCheckValue(def, v)}
                            </span>
                            <Mark ok={ok} />
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ---- wallet filters ---- */}
      {query.walletChecks.length > 0 && (
        <section className="bl-wd__group">
          <h3 className="eyebrow eyebrow-ink bl-wd__sub">Whole wallet</h3>
          <ul className="bl-wcheck">
            {query.walletChecks.map((chk) => {
              const def = CHECK_BY_ID[chk.checkId];
              const v = walletCheckValue(chk, positions, w, ctx);
              const ok = v !== undefined && compare(chk.operator, v, chk.value);
              return (
                <li key={chk.checkId} className="bl-wcheck__r" data-ok={ok}>
                  <CheckName checkId={chk.checkId} />
                  <span className="meta bl-cm__op">{checkLine(chk)}</span>
                  <span className="num bl-wcheck__v">
                    {v === undefined ? '—' : formatCheckValue(def, v)}
                  </span>
                  <Mark ok={ok} />
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <p className="bl-wd__foot meta">
        Generated wallet. Every figure here is recomputed from the position records above — nothing
        is a stored result, and no address in this corpus describes a real one. Positions traded in
        scope: {int(positions.length)}.
      </p>
    </Drawer>
  );
}
