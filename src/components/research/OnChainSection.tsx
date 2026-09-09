import { useState } from 'react';
import { useProject } from '../../lib/project-context';
import { Section, Block } from './Section';
import { AreaChart, PairedColumns } from '../primitives/Charts';
import { Gauge } from '../primitives/Meters';
import { Tag } from '../primitives/Bits';
import { int } from '../../lib/format';

const TONE: Record<string, string> = {
  good: 'var(--pos)',
  warn: 'var(--warn)',
  bad: 'var(--neg)',
};

/* small positions dark, large positions light — the ramp reads as a scale */
const BAND = ['var(--ink)', '#3d3d39', '#6b6a64', '#9a9891', '#c4c1b8'];

export function OnChainSection() {
  const { project, onchain } = useProject();
  const [distHot, setDistHot] = useState<number | null>(null);

  const m = project.metrics;
  const buyShare = (m.txns24h.buys / (m.txns24h.buys + m.txns24h.sells)) * 100;
  const param = project.parameters.find((p) => p.id === 'onchain');
  const sourced = onchain.readings.filter((r) => r.sourced).length;
  const maxBand = Math.max(...onchain.distribution.map((d) => d.pct));

  return (
    <Section
      id="onchain"
      index="03"
      title="On-Chain Intelligence"
      sub="Seven readings on ownership, launch mechanics and who is actually trading it."
      right={param ? <Tag tone="positive">Score {param.score}</Tag> : undefined}
      wide
    >
      {(seen) => (
        <>
          {/* ---------------- the meter wall ---------------- */}
          <div className="bl-gauges">
            {onchain.readings.map((r, i) => (
              <Gauge
                key={r.id}
                label={r.label}
                value={r.dial}
                display={r.display}
                caption={r.caption}
                color={TONE[r.tone]}
                sourced={r.sourced}
                run={seen}
                delay={i * 80}
              />
            ))}
          </div>

          <div className="bl-underrow">
            <span className="meta">
              <span className="bl-src" data-on="true" /> {sourced} sourced from Blockscout and
              DexScreener
            </span>
            <span className="meta">
              <span className="bl-src" data-on="false" />{' '}
              {onchain.readings.length - sourced} need cluster and launch-block analysis this build
              does not run
            </span>
          </div>

          <div className="bl-grid bl-grid--2">
            <Block title="Holder growth" note="Sample curve · endpoint is the sourced count">
              <AreaChart
                data={onchain.holderGrowth}
                height={180}
                run={seen}
                color="var(--ink)"
                valueFormat={(v) => int(v)}
              />
            </Block>

            <Block title="Buy / sell flow" note="Daily transaction counts">
              <PairedColumns data={onchain.buySell} height={152} run={seen} />
              <div className="bl-underrow">
                <span className="bl-legend">
                  <span className="bl-legend__k" style={{ background: 'var(--ink)' }} /> Buys
                  <span
                    className="bl-legend__k"
                    style={{ background: 'var(--rule-strong)', marginLeft: 14 }}
                  />{' '}
                  Sells
                </span>
                <span
                  className="meta"
                  style={{ color: buyShare >= 50 ? 'var(--pos)' : 'var(--neg)' }}
                >
                  {(m.txns24h.buys / Math.max(1, m.txns24h.sells)).toFixed(2)} : 1
                </span>
              </div>
            </Block>
          </div>

          <Block
            title="Position sizes"
            note={`${int(project.metrics.holders)} holders by band · sample`}
          >
            <ul className="bl-sizes" onMouseLeave={() => setDistHot(null)}>
              {onchain.distribution.map((d, i) => {
                const share = d.pct / maxBand;
                /* the label only goes inside when the bar is wide enough to
                   hold it, and it flips colour so it stays legible on the ramp */
                const inside = share >= 0.22;
                return (
                  <li
                    key={d.label}
                    className="bl-size"
                    data-on={distHot === i}
                    data-dim={distHot !== null && distHot !== i}
                    onMouseEnter={() => setDistHot(i)}
                  >
                    <span className="bl-size__band num">{d.label}</span>
                    <span className="bl-size__track">
                      <span
                        className="bl-size__bar"
                        style={{
                          width: seen ? `${share * 100}%` : 0,
                          background: BAND[i % BAND.length],
                          transitionDelay: `${i * 80}ms`,
                        }}
                      />
                      <span
                        className="bl-size__pct num"
                        data-inside={inside}
                        style={{
                          left: inside ? 10 : `calc(${share * 100}% + 10px)`,
                          color: inside && i < 2 ? 'var(--paper)' : 'var(--ink)',
                          opacity: seen ? 1 : 0,
                        }}
                      >
                        {d.pct}%
                      </span>
                    </span>
                    <span className="bl-size__n num">{int(d.wallets)}</span>
                    <span className="bl-size__u meta">wallets</span>
                  </li>
                );
              })}
            </ul>
            <div className="bl-underrow">
              <span className="meta">Smallest positions</span>
              <span className="meta">Largest positions</span>
            </div>
          </Block>
        </>
      )}
    </Section>
  );
}
