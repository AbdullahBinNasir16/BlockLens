import { useState } from 'react';
import { Section, Block } from './Section';
import { Tag, KV } from '../primitives/Bits';
import { MiniRing } from '../primitives/Meters';
import { signalColor, shortAddr } from '../../lib/format';
import { Icon } from '../app/Icons';
import { useCopy } from '../../lib/hooks';
import { useProject } from '../../lib/project-context';
import { XAvatar } from '../primitives/XAvatar';

export function DeveloperSection() {
  const { developer, deployerFacts } = useProject();
  const [open, setOpen] = useState<number | null>(developer.history.length - 1);
  const [copied, copy] = useCopy();

  return (
    <Section
      id="developer"
      index="02"
      title="Developer History"
      sub="Who deployed this before, and what happened to it."
      right={
        <Tag tone="ink">
          {developer.stats.deployments} deployment{developer.stats.deployments === 1 ? '' : 's'} ·{' '}
          {developer.stats.rugs} rugs
        </Tag>
      }
    >
      {(seen) => (
        <>
          {/* ---------------- profile ---------------- */}
          <div className="bl-dev">
            <div className="bl-dev__id">
              <span className="bl-dev__av">
                <XAvatar handle={developer.handle} size={44} />
              </span>
              <div>
                <p className="bl-dev__alias">{developer.alias}</p>
                <div className="bl-dev__handles">
                  <a
                    className="bl-dev__x meta"
                    href={`https://x.com/${developer.handle}`}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    @{developer.handle}
                  </a>
                  <span className="bl-ph__dot" />
                  <span className="meta">github.com/{developer.githubUser}</span>
                  <span className="bl-ph__dot" />
                  <button className="bl-ph__addr num" onClick={() => copy(developer.wallet)}>
                    {shortAddr(developer.wallet, 8, 5)}
                    <span className="bl-ph__copy">
                      {copied ? <Icon.Check size={12} /> : <Icon.Copy size={12} />}
                    </span>
                  </button>
                </div>
                <p className="bl-body bl-body--sm bl-dev__summary">{developer.summary}</p>
              </div>
            </div>

            <div className="bl-dev__conf">
              <MiniRing
                value={developer.identityConfidence}
                color="var(--ink)"
                size={70}
                stroke={4}
                run={seen}
              >
                <span style={{ fontSize: 14 }}>{developer.identityConfidence}</span>
              </MiniRing>
              <span className="eyebrow">Identity confidence</span>
              <span className="meta">
                {developer.doxxed ? 'Named individuals' : 'Pseudonymous'} · linked by repository and
                on-chain records
              </span>
            </div>
          </div>

          <div className="bl-factstrip">
            {deployerFacts.map((f) => (
              <div key={f.label} className="bl-fact">
                <span className="bl-fact__k eyebrow">{f.label}</span>
                <span className="bl-fact__v num" style={{ color: signalColor[f.signal] }}>
                  {f.value}
                </span>
              </div>
            ))}
          </div>

          {/* ---------------- deployment timeline ---------------- */}
          <Block title="Deployment timeline" note="Click a project for detail">
            <ol className="bl-timeline">
              {developer.history.map((h, i) => (
                <li
                  key={h.name}
                  className="bl-tl"
                  data-open={open === i}
                  data-current={!!h.current}
                >
                  <button className="bl-tl__hit" onClick={() => setOpen(open === i ? null : i)}>
                    <span className="bl-tl__year num">{h.year}</span>
                    <span className="bl-tl__rail" aria-hidden="true">
                      <span
                        className="bl-tl__node"
                        style={{ borderColor: signalColor[h.outcomeSignal] }}
                      />
                    </span>
                    <span className="bl-tl__body">
                      <span className="bl-tl__name">
                        {h.name} <span className="num bl-tl__tick">${h.ticker}</span>
                      </span>
                      <span className="bl-tl__meta">
                        <span
                          className="bl-tl__outcome"
                          style={{ color: signalColor[h.outcomeSignal] }}
                        >
                          {h.outcome}
                        </span>
                        <span className="meta">peak {h.peak}</span>
                        <span className="meta">{h.duration}</span>
                      </span>
                    </span>
                    <span className="bl-tl__chev" aria-hidden="true">
                      {open === i ? '−' : '+'}
                    </span>
                  </button>
                  {open === i && <p className="bl-tl__note">{h.note}</p>}
                </li>
              ))}
            </ol>
          </Block>

          <div className="bl-grid bl-grid--2">
            <Block title="Development activity" note="24 months, commit volume">
              <div className="bl-actbars">
                {developer.activity.map((v, i) => (
                  <span
                    key={i}
                    className="bl-actbar"
                    style={{
                      height: seen ? `${Math.max(6, v)}%` : '4%',
                      transitionDelay: `${i * 18}ms`,
                      background: i >= developer.activity.length - 3 ? 'var(--ink)' : 'var(--ink-5)',
                    }}
                    title={`${v}`}
                  />
                ))}
              </div>
              <div className="bl-actbars__x">
                <span className="meta">Sep 2024</span>
                <span className="meta">Sep 2026</span>
              </div>
            </Block>

            <Block title="Track record">
              <KV k="Deployments" v={developer.stats.deployments} />
              <KV k="Still active" v={developer.stats.activeProjects} tone="var(--pos)" />
              <KV k="Wound down" v={developer.stats.abandoned} tone="var(--warn)" />
              <KV k="Rugs / drains" v={developer.stats.rugs} tone="var(--pos)" />
              <KV k="First seen on-chain" v={developer.firstSeen} />
              <KV k="GitHub link" v="Verified" tone="var(--pos)" />
            </Block>
          </div>
        </>
      )}
    </Section>
  );
}
