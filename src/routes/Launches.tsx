import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/app/Icons';
import { bandColor, shortAddr, int } from '../lib/format';
import { fetchFeed, fetchSymbols, riskBand, type Feed, type ForwardRecord, type Launch } from '../lib/live/launches';

/* ============================================================
   Fresh Launches — every new Base pool, judged once at minute 5.

   Two signals and only two, because they are what the research can
   defend (backend/reports/model_card_v2.md, model_card_phase6.md).
   A pool that does not meet the scoring conditions shows why, never
   a number.
   ============================================================ */

const POLL_MS = 30_000;
type Show = 'scored' | 'all';

function ago(iso: string): string {
  const m = (Date.now() - Date.parse(iso)) / 60_000;
  if (m < 60) return `${Math.max(0, Math.round(m))}m`;
  return `${Math.floor(m / 60)}h ${Math.round(m % 60)}m`;
}

export function Launches() {
  const nav = useNavigate();
  const [feed, setFeed] = useState<Feed | null>(null);
  const [err, setErr] = useState('');
  const [show, setShow] = useState<Show>('scored');
  const [names, setNames] = useState<Record<string, { symbol: string; name: string }>>({});
  const [, tick] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const f = await fetchFeed();
        if (!alive) return;
        setFeed(f);
        setErr('');
        const want = f.launches.filter((l) => l.status === 'scored').map((l) => l.token);
        const missing = want.filter((t) => !(t in names));
        if (missing.length) {
          const got = await fetchSymbols(missing);
          if (alive) setNames((n) => ({ ...n, ...got }));
        }
      } catch (e) {
        if (alive) setErr(e instanceof Error ? e.message : String(e));
      }
    };
    load();
    const t = setInterval(load, POLL_MS);
    const c = setInterval(() => tick((n) => n + 1), 15_000);
    return () => {
      alive = false;
      clearInterval(t);
      clearInterval(c);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rows = useMemo(() => {
    const all = feed?.launches ?? [];
    return show === 'scored' ? all.filter((l) => l.status === 'scored') : all;
  }, [feed, show]);

  const counts = useMemo(() => {
    const c = { total: 0, scored: 0, waiting: 0, untraded: 0, pulled: 0 };
    for (const l of feed?.launches ?? []) {
      c.total++;
      if (l.status === 'scored') c.scored++;
      else if (l.status.startsWith('waiting')) c.waiting++;
      else if (l.status.includes('no trades')) c.untraded++;
      else if (l.status.includes('pulled')) c.pulled++;
    }
    return c;
  }, [feed]);

  const v = feed?.model.validation;

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Discovery · Base · Live</p>
          <h1 className="display d2">Fresh Launches</h1>
          <p className="bl-page__sub">
            Every new Base Uniswap pool, judged once at its five-minute mark by the two signals
            BlockLens's research supports.
          </p>
        </div>
        <div className="bl-page__headr bl-live">
          <span className="bl-live__state" data-status={err ? 'error' : feed ? 'live' : 'loading'}>
            <span className="bl-live__dot" />
            {err ? 'API unreachable' : feed ? 'Live' : 'Connecting'}
          </span>
          <span className="meta num">
            {feed?.last_run ? `Scanned ${ago(feed.last_run)} ago` : '—'}
          </span>
        </div>
      </header>

      {feed && (
        <section className="bl-launch__model">
          <div>
            <p className="eyebrow">Buyer-loss risk · {feed.model.version}</p>
            <p className="bl-launch__q">
              Will a buy at the minute-5 price be worth half or less six hours after launch?
            </p>
            <ul className="bl-launch__val meta">
              <li>
                PR-AUC <b className="num">{v!.in_period.pr_auc.toFixed(2)}</b> on {v!.in_period.tokens}{' '}
                launches, Jan–Apr 2026 (base rate {Math.round(v!.in_period.base_rate * 100)}%; a fixed
                rule checker scores {v!.in_period.rule_checker_pr_auc.toFixed(2)})
              </li>
              <li>
                Out of time: <b className="num">{v!.out_of_time.pr_auc.toFixed(2)}</b> on{' '}
                {v!.out_of_time.tokens} launches, Mar–Apr, trained before March
              </li>
              <li>
                May–Jul: flagged {v!.regime_check.flagged_at_0_5} of {v!.regime_check.tokens}, catching{' '}
                {v!.regime_check.losses_caught} of {v!.regime_check.losses} losses — few examples, read
                as suggestive
              </li>
            </ul>
          </div>
          <div>
            <p className="eyebrow">Launch type</p>
            <p className="bl-launch__q">Who holds the liquidity?</p>
            <ul className="bl-launch__val meta">
              <li>
                <b>Self-deployed</b>, deployer holds withdrawable liquidity: liquidity was pulled in{' '}
                {feed.model.launch_type_signal.self_deployed_rug_rate_eval} held-out launches
              </li>
              <li>
                <b>Launchpad</b>, minted and locked in one transaction:{' '}
                {feed.model.launch_type_signal.launchpad_rug_rate_eval}
              </li>
            </ul>
          </div>
        </section>
      )}

      {feed?.forward && <ForwardPanel f={feed.forward} />}

      <div className="bl-filters">
        <div className="bl-filters__grp">
          <span className="eyebrow">Show</span>
          <button className="bl-fchip" data-on={show === 'scored'} onClick={() => setShow('scored')}>
            Scored · {counts.scored}
          </button>
          <button className="bl-fchip" data-on={show === 'all'} onClick={() => setShow('all')}>
            All pools · {counts.total}
          </button>
        </div>
        <span className="meta num">
          last 6 hours: {counts.waiting} waiting for minute 5 · {counts.untraded} never traded ·{' '}
          {counts.pulled} drained before minute 5
        </span>
      </div>

      <div className="bl-tablewrap">
        <table className="bl-table bl-table--live">
          <thead>
            <tr>
              <th>Launched</th>
              <th>Token</th>
              <th>Launch type</th>
              <th className="bl-th--r">Buyer-loss risk</th>
              <th className="bl-th--r">Swaps by 5m</th>
              <th className="bl-th--r">Buyers by 5m</th>
              <th className="bl-th--r">Run-up by 5m</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <Row key={l.token} l={l} name={names[l.token]} onOpen={() => nav(`/app/token/${l.token}`)} />
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={9} className="bl-live__empty meta">
                  {err
                    ? `The BlockLens API is not answering (${err}). Start it with: uvicorn blocklens.api.app:app --port 8000`
                    : !feed
                      ? 'Connecting to the live feed…'
                      : 'No scored launches in the window yet. Scores appear five minutes after a pool is created.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="bl-page__foot meta">
        A score is given once, at launch + 5 minutes, and only to pools that traded by then and still
        held their liquidity. It is a model's estimate from{' '}
        {feed ? int(feed.model.trained_on.tokens) : '…'} labelled 2026 launches, not a finding about
        this token, and launch behaviour on Base has shifted more than once this year. Liquidity-pull
        risk is read from launch type, not from this score.
      </p>
    </div>
  );
}

function Row({ l, name, onOpen }: { l: Launch; name?: { symbol: string; name: string }; onOpen: () => void }) {
  const band = l.risk == null ? null : riskBand(l.risk);
  return (
    <tr className="bl-tr" onClick={onOpen}>
      <td className="meta num">{ago(l.launch_ts)}</td>
      <td>
        <span className="bl-tokencell__b">
          <span className="bl-tokencell__n">{name?.symbol || shortAddr(l.token, 6, 4)}</span>
          <span className="bl-tokencell__t meta" title={l.token}>
            {name?.name ? `${name.name} · ` : ''}
            {l.dex.replace('uniswap-', 'Uniswap ')}
          </span>
        </span>
      </td>
      <td>
        {l.launch_type ? (
          <span
            className="bl-tag"
            data-size="sm"
            data-tone={l.launch_type === 'self-deployed' ? 'negative' : undefined}
            title={
              l.launch_type === 'self-deployed'
                ? 'The deployer holds withdrawable liquidity'
                : 'Minted and given locked liquidity in one transaction'
            }
          >
            {l.launch_type === 'self-deployed' ? 'Self-deployed · liquidity withdrawable' : 'Launchpad · locked'}
          </span>
        ) : (
          <span className="meta">—</span>
        )}
      </td>
      <td className="bl-td--r">
        {l.risk == null ? (
          <span className="meta">—</span>
        ) : (
          <span className="bl-risk">
            <span className="bl-risk__bar">
              <span style={{ width: `${Math.round(l.risk * 100)}%`, background: bandColor[band!] }} />
            </span>
            <span className="num" style={{ color: bandColor[band!] }}>
              {Math.round(l.risk * 100)}%
            </span>
          </span>
        )}
      </td>
      <td className="bl-td--r num">{l.swaps_by_cutoff ?? '—'}</td>
      <td className="bl-td--r num">{l.buyers_by_cutoff ?? '—'}</td>
      <td className="bl-td--r num">
        {l.run_up_by_cutoff == null
          ? '—'
          : l.run_up_by_cutoff > 1000
            ? '>1000×'
            : `${l.run_up_by_cutoff.toFixed(l.run_up_by_cutoff < 10 ? 2 : 0)}×`}
      </td>
      <td className="meta">{l.status === 'scored' ? 'Scored at minute 5' : l.status.replace('not scored: ', '')}</td>
      <td className="bl-td--act">
        <span className="bl-rowacts">
          <a
            className="bl-iconbtn"
            href={`https://dexscreener.com/base/${l.pool}`}
            target="_blank"
            rel="noreferrer"
            title="Open on DexScreener"
            onClick={(e) => e.stopPropagation()}
          >
            <Icon.Ext size={13} />
          </a>
        </span>
      </td>
    </tr>
  );
}

/* The pre-registered forward record: predictions made before their outcome
   existed. Below the reporting floor it shows counts and says so. */
function ForwardPanel({ f }: { f: ForwardRecord }) {
  const b = f.buyer_loss;
  const ready = !!b.reportable;
  const lt7 = f.launch_type['7d'];
  return (
    <section className="bl-launch__fwd">
      <div className="bl-unres__sech">
        <h2 className="eyebrow">Forward record · predictions made before the outcome existed</h2>
        <span className="meta">
          {f.since ? `since ${new Date(f.since).toISOString().slice(0, 10)}` : 'starting'} · protocol fixed in advance
        </span>
      </div>
      <div className="bl-unres__grid">
        <div className="bl-stat">
          <span className="bl-stat__l eyebrow">Logged</span>
          <span className="bl-stat__v num">{int(f.logged)}</span>
          <span className="bl-stat__s meta">{int(f.scored)} scored at minute 5</span>
        </div>
        <div className="bl-stat">
          <span className="bl-stat__l eyebrow">Resolved at hour 6</span>
          <span className="bl-stat__v num">{int(b.resolved)}</span>
          <span className="bl-stat__s meta">
            {int(b.losses)} buyer losses · floor {f.report_floor.resolved} / {f.report_floor.losses}
          </span>
        </div>
        <div className="bl-stat">
          <span className="bl-stat__l eyebrow">Forward PR-AUC</span>
          <span className="bl-stat__v num">{ready && b.pr_auc != null ? b.pr_auc.toFixed(2) : '—'}</span>
          <span className="bl-stat__s meta">
            {ready
              ? `base rate ${Math.round((b.base_rate ?? 0) * 100)}%; margin ${b.pr_auc_minus_base_rate_ci
                  ? `${b.pr_auc_minus_base_rate_ci[0].toFixed(2)} to ${b.pr_auc_minus_base_rate_ci[1].toFixed(2)}`
                  : '—'}`
              : 'too early: below the pre-registered floor'}
          </span>
        </div>
        <div className="bl-stat">
          <span className="bl-stat__l eyebrow">Liquidity pulled by day 7</span>
          <span className="bl-stat__v num">
            {lt7?.['self-deployed'] ? `${Math.round(lt7['self-deployed'].rate * 100)}%` : '—'}
          </span>
          <span className="bl-stat__s meta">
            {lt7
              ? `self-deployed (${lt7['self-deployed']?.resolved ?? 0}) vs launchpad ${
                  lt7.launchpad ? `${Math.round(lt7.launchpad.rate * 100)}% (${lt7.launchpad.resolved})` : '—'}`
              : 'first results after 7 days'}
          </span>
        </div>
      </div>
      <AgentRow f={f} />
      {ready && (
        <p className="meta" style={{ marginTop: 12 }}>
          {b.pr_auc_minus_base_rate_ci && b.pr_auc_minus_base_rate_ci[0] > 0
            ? 'The model is beating the base rate on launches it had never seen, as pre-registered.'
            : 'The model is not yet beating the base rate on unseen launches; that is reported as a failure, not hidden.'}
        </p>
      )}
    </section>
  );
}

/* The paper agent: buys at minute 5 only when risk < 0.2 on a launchpad
   launch, sells at hour 6, 3% round-trip cost. Pre-registered (Phase 9). */
function AgentRow({ f }: { f: ForwardRecord }) {
  const p = f.paper_agent?.policies?.headline;
  if (!p) return null;
  const a = p.AGENT ?? { trades: 0 };
  const c = p.CONTROL ?? { trades: 0 };
  const pct = (x?: number) => (x == null ? '—' : `${x > 0 ? '+' : ''}${(x * 100).toFixed(1)}%`);
  const ready = !!p.reportable;
  return (
    <div className="bl-unres__grid" style={{ marginTop: 18 }}>
      <div className="bl-stat">
        <span className="bl-stat__l eyebrow">Paper agent · trades</span>
        <span className="bl-stat__v num">{a.trades}</span>
        <span className="bl-stat__s meta">
          buys only low-risk launchpad launches · floor {f.paper_agent!.floor}
        </span>
      </div>
      <div className="bl-stat">
        <span className="bl-stat__l eyebrow">Agent mean return</span>
        <span className="bl-stat__v num">{ready ? pct(a.mean) : '—'}</span>
        <span className="bl-stat__s meta">
          {ready ? `hit rate ${Math.round((a.hit_rate ?? 0) * 100)}% · after 3% costs` : 'too early: below the floor'}
        </span>
      </div>
      <div className="bl-stat">
        <span className="bl-stat__l eyebrow">Buy-everything control</span>
        <span className="bl-stat__v num">{ready ? pct(c.mean) : '—'}</span>
        <span className="bl-stat__s meta">
          {ready && p.agent_minus_control_ci
            ? `agent − control: ${pct(p.agent_minus_control_ci[0])} to ${pct(p.agent_minus_control_ci[1])}`
            : `${c.trades} control trades so far`}
        </span>
      </div>
    </div>
  );
}
