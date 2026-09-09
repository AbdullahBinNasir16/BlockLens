import { useState } from 'react';
import { Section } from './Section';
import { Tag, KV, Drawer } from '../primitives/Bits';
import { HolderBubbles } from '../primitives/HolderBubbles';
import { compact, int } from '../../lib/format';
import { useProject } from '../../lib/project-context';
import type { Holder } from '../../data/types';

export function WalletSection() {
  const { project, topHolders } = useProject();
  const [holder, setHolder] = useState<Holder | null>(null);

  const smart = topHolders.filter((h) => h.behaviour === 'smart').length;
  const sellers = topHolders.filter((h) => h.behaviour === 'seller').length;
  const combined = topHolders.reduce((a, h) => a + h.pct, 0);

  return (
    <Section
      id="wallets"
      index="04"
      title="Wallet Intelligence"
      sub="Every large position as a circle — sized by how much it holds, coloured by how it has behaved."
      right={<Tag tone="ink">{topHolders.length} wallets</Tag>}
      wide
    >
      {(seen) => (
        <>
          <HolderBubbles holders={topHolders} run={seen} onSelect={setHolder} />

          <div className="bl-factstrip">
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Wallets shown</span>
              <span className="bl-fact__v num">{topHolders.length}</span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Combined share</span>
              <span className="bl-fact__v num">{combined.toFixed(1)}%</span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Largest</span>
              <span className="bl-fact__v num">{topHolders[0]?.pct}%</span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Holding &amp; adding</span>
              <span className="bl-fact__v num" style={{ color: 'var(--pos)' }}>
                {smart}
              </span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Quick sellers</span>
              <span className="bl-fact__v num" style={{ color: 'var(--neg)' }}>
                {sellers}
              </span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Total holders</span>
              <span className="bl-fact__v num">{int(project.metrics.holders)}</span>
            </div>
          </div>

          <div className="bl-callout" data-tone="warn">
            <span className="bl-callout__m">!</span>
            <div>
              <p className="bl-callout__t">Ranks and balances are real; behaviour is not</p>
              <p className="bl-callout__d">
                The ten largest addresses and their shares come from Blockscout on Base. Everything
                below them, and the holding periods and behaviour classification on every circle,
                are sample values — separating a long-term holder from a quick seller needs
                per-wallet transfer history this build does not index.
              </p>
            </div>
          </div>

          <Drawer
            open={!!holder}
            onClose={() => setHolder(null)}
            eyebrow={holder ? `Rank ${holder.rank} · ${holder.behaviour}` : ''}
            title={holder?.label ?? ''}
          >
            {holder && (
              <>
                <p className="bl-drawer__addr num">{holder.address}</p>
                <div className="bl-drawer__tags">
                  <Tag
                    tone={
                      holder.behaviour === 'smart'
                        ? 'positive'
                        : holder.behaviour === 'seller'
                          ? 'negative'
                          : 'neutral'
                    }
                  >
                    {holder.behaviour === 'seller' ? 'quick seller' : holder.behaviour}
                  </Tag>
                  <Tag>Held {holder.held}</Tag>
                </div>
                <p className="bl-body bl-body--sm">{holder.note}</p>
                <div className="bl-drawer__stats">
                  <KV k="Share of supply" v={`${holder.pct}%`} />
                  <KV k="Value" v={`$${compact(holder.value)}`} />
                  <KV k="Holding period" v={holder.held} />
                  <KV
                    k="24h change"
                    v={
                      holder.change === 0
                        ? 'flat'
                        : `${holder.change > 0 ? '+' : ''}${holder.change}%`
                    }
                    tone={
                      holder.change === 0
                        ? undefined
                        : holder.change > 0
                          ? 'var(--pos)'
                          : 'var(--neg)'
                    }
                  />
                </div>
                <p className="meta bl-drawer__foot">
                  Behaviour classification and holding period are prototype sample values.
                </p>
              </>
            )}
          </Drawer>
        </>
      )}
    </Section>
  );
}
