import { useEffect, useMemo, useState } from 'react';
import { EmptyNote, Stat } from '../components/primitives/Bits';
import { int } from '../lib/format';
import { fetchFeed, type Feed } from '../lib/live/launches';
import { REASON_TONE, driftSeries, fetchHealth, reasonTotals, stackedDays, type Health } from '../lib/live/health';

/* ============================================================
   Model Health — the live system reporting on itself.

   Everything here is read from the forward log. It answers "is the
   scorer running, what is it seeing, and has the world moved", which is
   separate from "is the model right": that question belongs to the
   forward record on Fresh Launches and the Paper Agent page.
   ============================================================ */

type Load<T> = { state: 'loading' } | { state: 'ok'; value: T } | { state: 'error'; msg: string };

function ago(iso: string | null): string {
  if (!iso) return '—';
  const m = (Date.now() - Date.parse(iso)) / 60_000;
  if (m < 60) return `${Math.max(0, Math.round(m))} min ago`;
  if (m < 60 * 48) return `${Math.floor(m / 60)} h ago`;
  return `${Math.floor(m / 1440)} d ago`;
}

export function ModelHealth() {
  const [health, setHealth] = useState<Load<Health>>({ state: 'loading' });
  const [feed, setFeed] = useState<Feed | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      fetchHealth()
        .then((h) => alive && setHealth({ state: 'ok', value: h }))
        .catch((e) => alive && setHealth({ state: 'error', msg: String(e?.message ?? e) }));
      fetchFeed()
        .then((f) => alive && setFeed(f))
        .catch(() => alive && setFeed(null));
    };
    load();
    const t = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const h = health.state === 'ok' ? health.value : null;
  const stacked = useMemo(() => (h ? stackedDays(h.days) : []), [h]);
  const drift = useMemo(() => (h ? driftSeries(h.days) : []), [h]);
  const reasons = useMemo(() => (h ? reasonTotals(h.days) : []), [h]);
  const bins = feed?.forward?.buyer_loss?.reliability;
  const running = !!h?.scorer.last_run && Date.now() - Date.parse(h.scorer.last_run) < 5 * 60_000;

  return (
    <div className="bl-page bl-health">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Monitoring · Base · Live</p>
          <h1 className="display d2">Model Health</h1>
          <p className="bl-page__sub">
            Is the scorer running, what is it seeing, and has the launch population moved since the model was
            trained. Read from the forward log, refreshed every minute.
          </p>
        </div>
        <div className="bl-page__headr bl-live">
          <span className="bl-live__state" data-status={health.state === 'error' ? 'error' : running ? 'live' : h ? 'limited' : 'loading'}>
            <span className="bl-live__dot" />
            {health.state === 'error' ? 'API unreachable' : running ? 'Scorer running' : h ? 'Scorer stale' : 'Loading'}
          </span>
        </div>
      </header>

      {health.state === 'error' && (
        <EmptyNote title="The BlockLens API is not answering" detail={`${health.msg}. Start it with: uvicorn blocklens.api.app:app --port 8000`} />
      )}

      {h && (
        <>
          <section className="bl-unres__grid bl-health__status">
            <Stat label="Last scan" value={ago(h.scorer.last_run)} sub={h.scorer.scanned_to_block ? `to block ${int(h.scorer.scanned_to_block)}` : undefined} tone={running ? undefined : 'var(--warn)'} />
            <Stat label="Tracked now" value={int(h.scorer.tracked)} sub="pools in the six-hour window" />
            <Stat label="Logged" value={int(h.totals.logged)} sub={h.totals.since ? `since ${h.totals.since.slice(0, 10)}` : undefined} />
            <Stat label="Scored" value={int(h.totals.scored)} sub={`${int(h.totals.resolved)} resolved · ${int(h.totals.losses)} losses`} />
            <Stat label="Last error" value={h.scorer.last_error ? 'Yes' : 'None'} sub={h.scorer.last_error ?? 'the loop is healthy'} tone={h.scorer.last_error ? 'var(--neg)' : undefined} />
            <Stat label="Model" value={h.model.version} sub={h.model.trained ? `trained ${h.model.trained.slice(0, 10)}` : undefined} />
          </section>

          <section className="bl-health__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Launches a day, and why each was or was not scored</h2>
              <span className="meta">last {h.window_days} days</span>
            </div>
            {stacked.length ? (
              <>
                <Stacked days={stacked} />
                <ul className="bl-health__legend">
                  {reasons.map((r) => (
                    <li key={r.reason}>
                      <span className="bl-health__swatch" style={{ background: REASON_TONE[r.reason] }} />
                      <span>{r.reason}</span>
                      <b className="num">{int(r.count)}</b>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="meta">Nothing logged in the window yet.</p>
            )}
          </section>

          <section className="bl-health__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Launch-type drift · self-deployed share of scored launches</h2>
              <span className="meta">the regime that shifted from 4–11% to 63–69% in 2026</span>
            </div>
            {drift.some((d) => d.share != null) ? <Drift series={drift} /> : <p className="meta">No scored launches in the window yet.</p>}
            <p className="meta bl-health__note">
              The buyer-loss model is calibrated on a population; when the mix of launch types moves, its
              probabilities drift even if its ranking does not. This line is the early warning.
            </p>
          </section>

          <section className="bl-health__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Forward calibration · predicted against observed</h2>
              <span className="meta">
                {feed?.forward?.buyer_loss?.reportable ? 'above the pre-registered floor' : 'below the floor · counts only'}
              </span>
            </div>
            {bins && bins.length ? <Reliability bins={bins} /> : <p className="meta">No resolved predictions yet.</p>}
          </section>

          <section className="bl-health__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Outages · gaps in the record over {h.outage_threshold_minutes} minutes</h2>
              <span className="meta">{h.outages.length ? `${h.outages.length} in the window` : 'none in the window'}</span>
            </div>
            {h.outages.length > 0 && (
              <div className="bl-tablewrap">
                <table className="bl-table">
                  <thead>
                    <tr>
                      <th>From (UTC)</th>
                      <th>To (UTC)</th>
                      <th className="bl-th--r">Down for</th>
                    </tr>
                  </thead>
                  <tbody>
                    {h.outages.map((o) => (
                      <tr key={o.from}>
                        <td className="num">{o.from.slice(0, 16).replace('T', ' ')}</td>
                        <td className="num">{o.to.slice(0, 16).replace('T', ' ')}</td>
                        <td className="bl-td--r num">{o.minutes >= 120 ? `${(o.minutes / 60).toFixed(1)} h` : `${o.minutes} min`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="meta bl-health__note">
              Launches that fell due during an outage are logged as missed, never scored late, so a gap costs
              coverage but cannot leak an outcome into the forward record.
            </p>
          </section>
        </>
      )}

      <p className="bl-page__foot meta">
        Monitoring is separate from validation on purpose: this page says whether the system is working and
        what it is seeing; whether the model is right is answered only by the forward record.
      </p>
    </div>
  );
}

function Stacked({ days }: { days: ReturnType<typeof stackedDays> }) {
  const W = 900;
  const H = 180;
  const P = 24;
  const max = Math.max(1, ...days.map((d) => d.total));
  const bw = (W - P * 2) / days.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="bl-health__svg" role="img" aria-label="Launches a day by scoring outcome">
      {days.map((d, i) => {
        let y = H - P;
        return (
          <g key={d.day}>
            {d.parts.map((p) => {
              const hgt = (p.count / max) * (H - P * 2);
              y -= hgt;
              return <rect key={p.reason} x={P + i * bw + 2} y={y} width={Math.max(1, bw - 4)} height={hgt} fill={REASON_TONE[p.reason]} />;
            })}
            <text x={P + i * bw + bw / 2} y={H - 6} textAnchor="middle" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-4)">
              {d.day.slice(5)}
            </text>
            <text x={P + i * bw + bw / 2} y={y - 4} textAnchor="middle" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-2)">
              {d.total}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function Drift({ series }: { series: ReturnType<typeof driftSeries> }) {
  const W = 900;
  const H = 150;
  const P = 24;
  const pts = series.filter((s) => s.share != null);
  const x = (i: number) => P + (i / Math.max(1, series.length - 1)) * (W - P * 2);
  const y = (v: number) => P + (1 - v) * (H - P * 2);
  const d = series
    .map((s, i) => (s.share == null ? null : `${x(i).toFixed(1)},${y(s.share).toFixed(1)}`))
    .filter(Boolean)
    .map((p, i) => `${i ? 'L' : 'M'}${p}`)
    .join('');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="bl-health__svg" role="img" aria-label="Self-deployed share per day">
      {[0, 0.5, 1].map((v) => (
        <g key={v}>
          <line x1={P} x2={W - P} y1={y(v)} y2={y(v)} stroke="var(--rule)" strokeWidth="1" />
          <text x={W - P + 4} y={y(v) + 3} fontFamily="var(--mono)" fontSize="9" fill="var(--ink-4)">
            {Math.round(v * 100)}%
          </text>
        </g>
      ))}
      {pts.length > 1 && <path d={d} fill="none" stroke="var(--neg)" strokeWidth="1.6" />}
      {series.map((s, i) =>
        s.share == null ? null : (
          <g key={s.day}>
            <circle cx={x(i)} cy={y(s.share)} r="3" fill="var(--neg)" />
            <text x={x(i)} y={H - 6} textAnchor="middle" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-4)">
              {s.day.slice(5)}
            </text>
          </g>
        )
      )}
    </svg>
  );
}

function Reliability({ bins }: { bins: { bin: string; n: number; mean_predicted: number; observed: number }[] }) {
  const W = 900;
  const H = 180;
  const P = 24;
  const bw = (W - P * 2) / bins.length;
  const y = (v: number) => P + (1 - v) * (H - P * 2);
  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} className="bl-health__svg" role="img" aria-label="Predicted against observed loss rate by bin">
        {bins.map((b, i) => (
          <g key={b.bin}>
            <rect x={P + i * bw + 4} y={y(b.mean_predicted)} width={bw / 2 - 5} height={H - P - y(b.mean_predicted)} fill="var(--ink-4)" />
            <rect x={P + i * bw + bw / 2 + 1} y={y(b.observed)} width={bw / 2 - 5} height={H - P - y(b.observed)} fill="var(--ink)" />
            <text x={P + i * bw + bw / 2} y={H - 6} textAnchor="middle" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-4)">
              {b.bin}
            </text>
            <text x={P + i * bw + bw / 2} y={P - 6} textAnchor="middle" fontFamily="var(--mono)" fontSize="9" fill="var(--ink-2)">
              n={b.n}
            </text>
          </g>
        ))}
      </svg>
      <p className="meta bl-health__note">
        <span className="bl-health__swatch" style={{ background: 'var(--ink-4)' }} /> mean predicted ·{' '}
        <span className="bl-health__swatch" style={{ background: 'var(--ink)' }} /> observed loss rate, per risk bin. A calibrated
        model has the two bars level in every bin.
      </p>
    </>
  );
}
