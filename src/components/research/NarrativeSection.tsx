import { useState } from 'react';
import { useProject } from '../../lib/project-context';
import { Section, Block } from './Section';
import { ArcMeter, BarScale } from '../primitives/Meters';
import { Tag } from '../primitives/Bits';
import { qualityBand, qualityColor } from '../../lib/format';

const PHASE_TONE: Record<string, string> = {
  Emerging: 'var(--info)',
  Expanding: 'var(--pos)',
  Peaking: 'var(--warn)',
  Cooling: 'var(--neg)',
};

export function NarrativeSection() {
  const { project, narrative } = useProject();
  const { nodes: narrativeMap, edges: narrativeEdges, reading: narrativeReading } = narrative;
  const [hot, setHot] = useState<string | null>(null);
  const byId = Object.fromEntries(narrativeMap.map((n) => [n.id, n]));
  const active = hot ? byId[hot] : null;

  const linked = (id: string) =>
    narrativeEdges.filter((e) => e.includes(id)).flat().filter((x) => x !== id);
  const lit = hot ? new Set([hot, ...linked(hot)]) : null;

  return (
    <Section
      id="narrative"
      index="09"
      title="Narrative & Meta"
      sub="Where the project sits in the current market story, and whether that story is still expanding."
      right={<Tag tone="positive">{project.narrative.primary}</Tag>}
      wide
    >
      {(seen) => (
        <div className="bl-grid bl-grid--split">
          <Block title="Narrative map" note="Hover a node to trace its links">
            <div className="bl-nmap">
              <svg viewBox="0 0 200 132" className="bl-nmap__svg" onMouseLeave={() => setHot(null)}>
                {narrativeEdges.map(([a, b], i) => {
                  const na = byId[a];
                  const nb = byId[b];
                  const on = lit ? lit.has(a) && lit.has(b) : false;
                  return (
                    <line
                      key={i}
                      x1={na.x}
                      y1={na.y}
                      x2={nb.x}
                      y2={nb.y}
                      stroke={on ? 'var(--ink)' : 'var(--rule-strong)'}
                      strokeWidth={on ? 0.9 : 0.5}
                      opacity={lit && !on ? 0.18 : seen ? 1 : 0}
                      style={{ transition: `opacity 400ms var(--ease) ${i * 40}ms` }}
                    />
                  );
                })}

                {narrativeMap.map((n, i) => {
                  const r = 5 + (n.strength / 100) * 8;
                  const on = lit ? lit.has(n.id) : false;
                  const core = n.id === 'core';
                  return (
                    <g
                      key={n.id}
                      opacity={lit && !on ? 0.24 : seen ? 1 : 0}
                      style={{
                        transition: `opacity 400ms var(--ease) ${i * 50}ms`,
                        cursor: 'default',
                      }}
                      onMouseEnter={() => setHot(n.id)}
                    >
                      <circle
                        cx={n.x}
                        cy={n.y}
                        r={r}
                        fill={core ? 'var(--ink)' : 'var(--paper)'}
                        stroke={core ? 'var(--ink)' : PHASE_TONE[n.phase]}
                        strokeWidth={hot === n.id ? 1.6 : 1}
                      />
                      <text
                        x={n.x}
                        y={n.y + r + 6}
                        textAnchor="middle"
                        fontFamily="var(--mono)"
                        fontSize="4.4"
                        fill={core ? 'var(--ink)' : 'var(--ink-2)'}
                        stroke="var(--paper)"
                        strokeWidth="1.8"
                        paintOrder="stroke"
                        style={{ pointerEvents: 'none' }}
                      >
                        {n.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
              <div className="bl-nmap__key">
                {(['Emerging', 'Expanding', 'Cooling'] as const).map((p) => (
                  <span key={p} className="bl-legend">
                    <span className="bl-legend__k" style={{ background: PHASE_TONE[p] }} /> {p}
                  </span>
                ))}
              </div>
            </div>
          </Block>

          <Block title="Reading">
            <div className="bl-narrread">
              <ArcMeter
                value={project.narrative.relevance}
                color={qualityColor[qualityBand(project.narrative.relevance)]}
                width={172}
                run={seen}
              />
              <div className="bl-narrread__v">
                <span className="bl-conc__v num">{project.narrative.relevance}</span>
                <span className="eyebrow">Relevance / 100</span>
              </div>
            </div>

            <ul className="bl-consist">
              {narrativeReading.map((r, i) => (
                <li key={r.label} className="bl-consistrow">
                  <span className="bl-consistrow__t">
                    <span className="bl-consistrow__l">{r.label}</span>
                    <span
                      className="num bl-consistrow__v"
                      style={{ color: qualityColor[qualityBand(r.value)] }}
                    >
                      {r.value}
                    </span>
                  </span>
                  <BarScale
                    value={r.value}
                    color={qualityColor[qualityBand(r.value)]}
                    height={3}
                    run={seen}
                    delay={i * 70}
                  />
                  <span className="meta">{r.note}</span>
                </li>
              ))}
            </ul>

            {active && (
              <div className="bl-narrhot">
                <span className="eyebrow eyebrow-ink">{active.label}</span>
                <span className="meta" style={{ color: PHASE_TONE[active.phase] }}>
                  {active.phase} · strength {active.strength}
                </span>
                <span className="meta">{active.relation}</span>
              </div>
            )}
          </Block>
        </div>
      )}
    </Section>
  );
}
