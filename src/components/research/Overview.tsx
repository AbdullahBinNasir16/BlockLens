import { useState } from 'react';
import { ScoreRing } from '../primitives/ScoreRing';
import { MiniRing, Radar, BarScale } from '../primitives/Meters';
import { useInView } from '../../lib/hooks';
import { useProject } from '../../lib/project-context';
import { bandColor, qualityBand, qualityColor, riskBand, signalColor } from '../../lib/format';

export function Overview() {
  const { project } = useProject();
  const [ref, seen] = useInView<HTMLElement>('0px 0px -5% 0px');
  const [hot, setHot] = useState<number | null>(null);

  const p = project.parameters;
  const active = hot === null ? null : p[hot];
  const rBand = riskBand(project.scores.risk);

  return (
    <section className="bl-ov" id="overview" ref={ref}>
      {/* ---------------- headline scores ---------------- */}
      <div className="bl-ov__scores">
        <div className="bl-ov__rings">
          <div className="bl-ov__ring">
            <ScoreRing
              value={project.scores.risk}
              label="Overall Risk"
              caption={`${rBand} risk`}
              color={bandColor[rBand]}
              run={seen}
              size={214}
            />
          </div>
          <span className="bl-ov__div" aria-hidden="true" />
          <div className="bl-ov__ring">
            <ScoreRing
              value={project.scores.confidence}
              label="Confidence"
              caption="evidence coverage"
              color="var(--ink)"
              run={seen}
              size={214}
              delay={160}
            />
          </div>
        </div>

        <div className="bl-ov__verdict">
          <p className="eyebrow">Reading</p>
          <p className="bl-ov__vline">
            Risk is <strong style={{ color: bandColor[rBand] }}>{rBand}</strong> and confidence is{' '}
            <strong>
              {project.scores.confidence >= 80
                ? 'high'
                : project.scores.confidence >= 60
                  ? 'moderate'
                  : 'low'}
            </strong>
            . Conviction: <strong>{project.scores.conviction}</strong>.
          </p>
          <p className="bl-ov__vnote">
            The score is a summary of the {p.length} parameters below — not the assessment itself.
          </p>
          <a className="bl-ov__jump" href="#assessment">
            Jump to final assessment <span aria-hidden="true">↓</span>
          </a>
        </div>
      </div>

      {/* ---------------- parameter assessment ---------------- */}
      <div className="bl-params">
        <div className="bl-params__head">
          <span className="eyebrow eyebrow-ink">Parameter assessment</span>
          <span className="meta">Hover a parameter to see what moved it</span>
        </div>

        <div className="bl-params__grid">
          <div className="bl-params__radar">
            <Radar
              points={p.map((x) => ({ label: x.label, value: x.score }))}
              size={280}
              run={seen}
              activeIndex={hot}
              onHover={setHot}
            />
            <p className="meta bl-params__radarnote">
              {active ? active.label : `${p.length} scored parameters`}
            </p>
          </div>

          <ul className="bl-params__list" onMouseLeave={() => setHot(null)}>
            {p.map((x, i) => {
              const band = qualityBand(x.score);
              return (
                <li
                  key={x.id}
                  className="bl-param"
                  data-on={hot === i}
                  data-dim={hot !== null && hot !== i}
                  onMouseEnter={() => setHot(i)}
                >
                  <MiniRing
                    value={x.score}
                    color={qualityColor[band]}
                    size={44}
                    stroke={3}
                    run={seen}
                    delay={i * 40}
                  >
                    <span style={{ fontSize: 11.5 }}>{x.score}</span>
                  </MiniRing>
                  <span className="bl-param__l">{x.label}</span>
                </li>
              );
            })}
          </ul>

          <div className="bl-params__inspect">
            {active ? (
              <>
                <div className="bl-inspect__h">
                  <span className="eyebrow eyebrow-ink">{active.label}</span>
                  <span
                    className="bl-inspect__score num"
                    style={{ color: qualityColor[qualityBand(active.score)] }}
                  >
                    {active.score}
                  </span>
                </div>
                <p className="bl-inspect__note">{active.note}</p>
                <p className="eyebrow bl-inspect__dl">Contributing signals</p>
                <ul className="bl-drivers">
                  {active.drivers.map((d) => (
                    <li key={d.label} className="bl-driver">
                      <span className="bl-driver__t">
                        <span
                          className="bl-driver__dot"
                          style={{ background: signalColor[d.signal] }}
                        />
                        {d.label}
                      </span>
                      <span className="bl-driver__w">
                        <BarScale value={d.weight} color={signalColor[d.signal]} height={2} />
                        <span className="meta">{d.weight}%</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <div className="bl-inspect__idle">
                <p className="eyebrow">Weakest parameters</p>
                <ul className="bl-weak">
                  {[...p]
                    .sort((a, b) => a.score - b.score)
                    .slice(0, 3)
                    .map((x) => (
                      <li key={x.id}>
                        <span className="bl-weak__l">{x.label}</span>
                        <span
                          className="bl-weak__v num"
                          style={{ color: qualityColor[qualityBand(x.score)] }}
                        >
                          {x.score}
                        </span>
                      </li>
                    ))}
                </ul>
                <p className="bl-inspect__note">
                  These three carry the assessment down. Everything else scores{' '}
                  {[...p].sort((a, b) => a.score - b.score)[3]?.score ?? 0} or above.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
