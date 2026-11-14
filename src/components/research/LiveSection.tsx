import { useProject, useProjectLive } from '../../lib/project-context';
import { compact, int } from '../../lib/format';
import { EmptyNote, ProvChip, SectionHead, Stat } from '../primitives/Bits';
import { RiskPanel } from '../live/RiskPanel';

/* ============================================================
   The live section of a case study (Phase 7).

   Everything here comes from the BlockLens API, fetched now: contract
   flags and holders (GoPlus), the market (DexScreener) and the model's
   view of this token. Nothing here is sample, so when the API cannot be
   reached the section says so instead of filling in.
   ============================================================ */

export function LiveSection() {
  const { project } = useProject();
  const live = useProjectLive();
  const d = live.provenance === 'live' ? live.data : null;
  const sec = d?.security.data ?? null;
  const top = d?.market.data?.pairs[0];

  return (
    <section className="bl-sec" id="live" data-seen="true">
      <SectionHead
        index="L"
        title="Live: market, contract and model"
        sub="Fetched now through the BlockLens API. The research sections below it are sample."
        right={
          d ? (
            <ProvChip live note="From the BlockLens API, fetched just now." />
          ) : (
            <ProvChip live={false} empty why={live.loading ? 'loading' : 'the API is not reachable'} />
          )
        }
      />
      <div className="bl-sec__body">
        {!d ? (
          <EmptyNote
            title={live.loading ? 'Loading live data…' : 'Live data is unavailable'}
            detail={
              live.loading
                ? `Asking the BlockLens API about ${project.ticker}.`
                : `The API could not be used (${live.reason}). Market figures, contract flags and the model's view are not shown, and no sample stands in for them. The header shows the ${project.ticker} snapshot instead, badged as sample.`
            }
          />
        ) : (
          <>
            <div className="bl-unres__grid">
              <Stat
                label="Honeypot"
                value={sec?.honeypot == null ? 'Unknown' : sec.honeypot ? 'Flagged' : 'Not flagged'}
                tone={sec?.honeypot ? 'var(--neg)' : undefined}
                sub={d.security.error ? `GoPlus unavailable: ${d.security.error.replace(/^goplus: /, '')}` : 'GoPlus simulation'}
              />
              <Stat label="Holders" value={sec?.holders ? int(sec.holders) : '—'} sub={sec?.holders === 0 ? 'not yet indexed by GoPlus' : 'GoPlus'} />
              <Stat
                label="Top 10 hold"
                value={sec?.top10Pct == null ? '—' : `${sec.top10Pct.toFixed(1)}%`}
                tone={sec?.top10Pct != null && sec.top10Pct >= 50 ? 'var(--warn)' : undefined}
                sub="share of supply"
              />
              <Stat
                label="Deepest pool"
                value={top ? `$${compact(Math.round(top.liquidity))}` : '—'}
                sub={top ? `${top.dex} · ${top.quote}` : d.market.error ?? 'no Base pair listed'}
              />
            </div>
            <RiskPanel risk={d.risk} />
          </>
        )}
      </div>
    </section>
  );
}
