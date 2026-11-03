import type { TokenRiskResponse } from '../../data/api';
import type { Explanation } from '../../lib/live/launches';
import { ProvChip, Stat } from '../primitives/Bits';
import { Explain } from './Explain';

/* ============================================================
   The model's view of one token (Phase 7, Part D).

   Two rules:
   - A score appears only when the model was built to give one: a launch
     the live feed scored at its own minute 5. Anything else shows its
     state and the reason, in words, with the model's card.
   - The score is read as what happened forward to launches scored in the
     same band ("of 70 launches scored like this, 34 lost half by hour 6"),
     not as the raw model output, because the raw output is not calibrated
     forward (DECISIONS.md, Phase 8 result). The raw score is shown too,
     labelled as a ranking, beside the inputs that produced it.
   ============================================================ */

const STATE_TITLE: Record<TokenRiskResponse['state'], string> = {
  scored: 'Scored at minute 5',
  pending: 'Waiting for minute 5',
  not_scored: 'Seen, not scored',
  out_of_scope: "Outside the model's scope",
};

const date = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export function RiskPanel({ risk, unavailable }: { risk: TokenRiskResponse | null; unavailable?: string }) {
  if (!risk) {
    return (
      <section className="bl-unres__sec bl-risk-panel">
        <div className="bl-unres__sech">
          <h2 className="eyebrow">Model risk</h2>
          <ProvChip live={false} empty why="the API is not reachable" />
        </div>
        <p className="meta">
          The model's view comes only from the BlockLens API{unavailable ? ` (${unavailable})` : ''}. No sample
          score is ever shown in its place.
        </p>
      </section>
    );
  }
  const m = risk.model;
  const s = risk.score;
  return (
    <section className="bl-unres__sec bl-risk-panel" data-state={risk.state}>
      <div className="bl-unres__sech">
        <h2 className="eyebrow">Model risk · {STATE_TITLE[risk.state]}</h2>
        <ProvChip live note={`From the BlockLens API, model ${m.version}`} />
      </div>

      {s ? (
        <>
          {s.band ? (
            <p className="bl-risk-panel__lede">
              Of <b className="num">{s.band.launches.toLocaleString()}</b> launches the model scored like this
              (between {s.band.lo.toFixed(1)} and {s.band.hi.toFixed(1)}) since {date(s.band.since)},{' '}
              <b className="num">{s.band.losses.toLocaleString()}</b> lost half their value or more by hour 6:
              about <b className="num">{Math.round(s.band.observed * 100)} in 100</b>.
            </p>
          ) : (
            <p className="bl-risk-panel__lede">
              No forward record exists yet for launches scored in this band, so there is no measured rate to
              quote.
            </p>
          )}
          <div className="bl-unres__grid">
            <Stat
              label="Model score"
              value={s.risk.toFixed(2)}
              sub="a ranking, not a probability: forward, the raw scores ran about four times too high"
            />
            <Stat
              label="Launch type"
              value={s.launchType === 'self-deployed' ? 'Self-deployed' : s.launchType === 'launchpad' ? 'Launchpad' : '—'}
              sub={
                s.launchType === 'self-deployed'
                  ? 'deployer holds withdrawable liquidity: 89% pulled within 7 days, forward'
                  : s.launchType === 'launchpad'
                    ? 'liquidity locked at launch: 0.6% pulled within 7 days, forward'
                    : undefined
              }
              tone={s.launchType === 'self-deployed' ? 'var(--neg)' : undefined}
            />
            <Stat label="Scored" value={date(s.scoredAt)} sub="once, at launch + 5 minutes" />
          </div>
          {s.drivers.length > 0 && (
            <div className="bl-unres__why">
              <p className="eyebrow">The inputs that produced this score</p>
              <Explain
                why={
                  {
                    base_rate: s.baseRate,
                    risk: s.risk,
                    drivers: s.drivers,
                    rest: s.rest,
                    base_logit: 0,
                    logit: 0,
                    unit: 'log-odds',
                  } as Explanation
                }
              />
            </div>
          )}
          <p className="meta" style={{ marginTop: 12 }}>
            {risk.reason} The buyer-loss label counts a price fall, not a liquidity pull: read the launch type
            first.
          </p>
        </>
      ) : (
        <div className="bl-risk-panel__scope">
          <p className="bl-risk-panel__lede">{risk.reason}</p>
        </div>
      )}

      <dl className="bl-risk-panel__card meta">
        <div>
          <dt>Model</dt>
          <dd>{m.version}</dd>
        </div>
        <div>
          <dt>Predicts</dt>
          <dd>{m.target}</dd>
        </div>
        <div>
          <dt>Trained on</dt>
          <dd>
            {m.trainedOnTokens.toLocaleString()} launches, {m.trainedOnLaunches.join(' to ')}; trained{' '}
            {m.trainedAt}
          </dd>
        </div>
        <div>
          <dt>Applies to</dt>
          <dd>{m.appliesTo}</dd>
        </div>
      </dl>
    </section>
  );
}
