import { ScoreRing } from '../primitives/ScoreRing';
import { DotScale } from '../primitives/Meters';
import { useInView } from '../../lib/hooks';
import { useProject } from '../../lib/project-context';
import { bandColor, riskBand, signalColor } from '../../lib/format';

const MARK: Record<string, string> = { positive: '+', negative: '−', neutral: '~' };

export function FinalAssessment() {
  const { project } = useProject();
  const [ref, seen] = useInView<HTMLElement>('0px 0px -6% 0px');
  const s = project.scores;
  const band = riskBand(s.risk);
  const bullets = project.assessment.bullets;

  return (
    <section className="bl-final" id="assessment" ref={ref}>
      <div className="bl-final__head">
        <span className="eyebrow eyebrow-ink">11 — Final</span>
        <h2 className="display d2">Overall Assessment</h2>
      </div>

      <div className="bl-final__body">
        <div className="bl-final__ring">
          <ScoreRing
            value={s.risk}
            label="Overall Risk"
            caption={`${band} risk`}
            color={bandColor[band]}
            run={seen}
            size={244}
          />
        </div>

        <div className="bl-final__read">
          <div className="bl-final__stats">
            <div className="bl-finalstat">
              <span className="eyebrow">Risk</span>
              <span className="bl-finalstat__v" style={{ color: bandColor[band] }}>
                {band[0].toUpperCase() + band.slice(1)}
              </span>
              <DotScale value={s.risk} color={bandColor[band]} count={10} dot={6} run={seen} />
            </div>
            <div className="bl-finalstat">
              <span className="eyebrow">Confidence</span>
              <span className="bl-finalstat__v">{s.confidence}%</span>
              <DotScale
                value={s.confidence}
                color="var(--ink)"
                count={10}
                dot={6}
                run={seen}
                delay={140}
              />
            </div>
            <div className="bl-finalstat">
              <span className="eyebrow">Conviction</span>
              <span className="bl-finalstat__v">{s.conviction}</span>
              <DotScale value={82} color="var(--ink)" count={10} dot={6} run={seen} delay={280} />
            </div>
          </div>

          <ul className="bl-verdict">
            {bullets.map((b, i) => (
              <li
                key={b.text}
                className="bl-verdict__i"
                style={{
                  opacity: seen ? 1 : 0,
                  transform: seen ? 'none' : 'translate3d(0,6px,0)',
                  transition: `opacity 340ms var(--ease) ${i * 60}ms, transform 340ms var(--ease) ${
                    i * 60
                  }ms`,
                }}
              >
                <span className="bl-verdict__m" style={{ color: signalColor[b.signal] }}>
                  {MARK[b.signal]}
                </span>
                <span className="bl-verdict__t">{b.text}</span>
              </li>
            ))}
          </ul>

          <p className="meta bl-final__disclaim">
            Market, repository and roadmap figures captured {project.snapshotAt}. Scores, wallet
            detail and promoter data are prototype sample values, not findings about {project.name}.
            Not financial advice.
          </p>
        </div>
      </div>
    </section>
  );
}
