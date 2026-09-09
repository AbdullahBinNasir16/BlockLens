import { useState } from 'react';
import { useInView } from '../../lib/hooks';
import { Logo } from '../primitives/Logo';

const STEPS = [
  { k: 'Contract Address', d: 'The only input.' },
  { k: 'Discover', d: 'Resolve token, chain, pair, deployer.' },
  { k: 'Collect', d: 'Chain state, repositories, accounts, documents.' },
  { k: 'Analyze', d: 'Score each dimension independently.' },
  { k: 'Connect', d: 'Link wallets, people, and prior projects.' },
  { k: 'Research', d: 'Test every claim against evidence.' },
  { k: 'Understand', d: 'Weigh the findings against each other.' },
  { k: 'BlockLens Intelligence', d: 'A complete profile. The score is only the summary.' },
];

const DIMENSIONS = [
  'Project Overview',
  'Idea & Fundamentals',
  'Website & Documentation',
  'Developer Intelligence',
  'KOL / Promotion Intelligence',
  'X Authenticity',
  'Social Intelligence',
  'On-Chain Intelligence',
  'Wallet Intelligence',
  'Risk Analysis',
  'Evidence & Sources',
  'Final Assessment',
  'Narrative / Meta',
  'Meme / Lore Intelligence',
  'Historical Analysis',
  'DEX & Liquidity',
  'Tokenomics & Holders',
  'Relationship Intelligence',
];

const R_DOT = 236;
const R_TEXT = 252;
const R_IN = 118;
const CX = 460;
const CY = 460;

export function FlowSection() {
  const [ref, seen] = useInView<HTMLElement>();
  const [hot, setHot] = useState<number | null>(null);

  return (
    <section className="bl-flow" ref={ref}>
      <div className="bl-flow__grid">
        {/* ---------------- the pipeline ---------------- */}
        <div className="bl-flow__pipe">
          <p className="eyebrow">The process</p>
          <h2 className="display d3 bl-flow__h">
            One input.
            <br />
            Seven passes.
          </h2>

          <ol className="bl-pipe">
            {STEPS.map((s, i) => (
              <li
                key={s.k}
                className="bl-pipe__step"
                data-last={i === STEPS.length - 1}
                style={{
                  opacity: seen ? 1 : 0,
                  transform: seen ? 'none' : 'translate3d(0,10px,0)',
                  transition: `opacity 420ms var(--ease) ${i * 70}ms, transform 420ms var(--ease) ${
                    i * 70
                  }ms`,
                }}
              >
                <span className="bl-pipe__rail" aria-hidden="true">
                  <span className="bl-pipe__node" />
                </span>
                <span className="bl-pipe__body">
                  <span className="bl-pipe__k">{s.k}</span>
                  <span className="bl-pipe__d">{s.d}</span>
                </span>
                <span className="bl-pipe__n meta">{String(i + 1).padStart(2, '0')}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* ---------------- the dimension map ---------------- */}
        <div className="bl-flow__map">
          <p className="eyebrow bl-flow__maplabel">What it looks at</p>
          <div className="bl-radialwrap">
            <svg viewBox="0 0 920 920" className="bl-radial" onMouseLeave={() => setHot(null)}>
              {DIMENSIONS.map((d, i) => {
                const a = ((i / DIMENSIONS.length) * 360 - 90) * (Math.PI / 180);
                const cos = Math.cos(a);
                const sin = Math.sin(a);
                const x1 = CX + cos * R_IN;
                const y1 = CY + sin * R_IN;
                const x2 = CX + cos * (R_DOT - 8);
                const y2 = CY + sin * (R_DOT - 8);
                const dx = CX + cos * R_DOT;
                const dy = CY + sin * R_DOT;
                const tx = CX + cos * R_TEXT;
                const ty = CY + sin * R_TEXT;
                const anchor = cos > 0.12 ? 'start' : cos < -0.12 ? 'end' : 'middle';
                const on = hot === i;
                const dim = hot !== null && !on;

                return (
                  <g
                    key={d}
                    opacity={seen ? (dim ? 0.24 : 1) : 0}
                    style={{
                      transition: `opacity 420ms var(--ease) ${seen ? i * 34 : 0}ms`,
                      cursor: 'default',
                    }}
                    onMouseEnter={() => setHot(i)}
                  >
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={on ? 'var(--ink)' : 'var(--rule-strong)'}
                      strokeWidth={on ? 1.3 : 0.8}
                    />
                    <circle
                      cx={dx}
                      cy={dy}
                      r={on ? 4.4 : 3}
                      fill={on ? 'var(--ink)' : 'var(--paper)'}
                      stroke="var(--ink)"
                      strokeWidth="1.1"
                    />
                    <text
                      x={tx + (anchor === 'start' ? 10 : anchor === 'end' ? -10 : 0)}
                      y={ty + 4}
                      textAnchor={anchor}
                      fontFamily="var(--mono)"
                      fontSize="13.5"
                      letterSpacing="0.02em"
                      fill={on ? 'var(--ink)' : 'var(--ink-2)'}
                    >
                      {d}
                    </text>
                    {/* invisible hit target so short labels are easy to hover */}
                    <rect
                      x={anchor === 'end' ? tx - 210 : anchor === 'middle' ? tx - 105 : tx}
                      y={ty - 12}
                      width="210"
                      height="24"
                      fill="transparent"
                    />
                  </g>
                );
              })}
              <circle
                cx={CX}
                cy={CY}
                r={R_IN - 14}
                fill="none"
                stroke="var(--rule)"
                strokeWidth="1"
                strokeDasharray="2 5"
              />
            </svg>
            <span className="bl-radial__center">
              <Logo size={30} />
            </span>
          </div>
          <p className="bl-flow__mapnote meta">
            Eighteen dimensions. Every one of them can move the assessment.
          </p>
        </div>
      </div>
    </section>
  );
}
