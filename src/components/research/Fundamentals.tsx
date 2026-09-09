import { Section, Block } from './Section';
import { ArcMeter } from '../primitives/Meters';
import { Tag } from '../primitives/Bits';
import { useProject } from '../../lib/project-context';
import { qualityBand, qualityColor, signalColor } from '../../lib/format';

export function Fundamentals() {
  const { project } = useProject();
  const f = project.fundamentals;

  return (
    <Section
      id="fundamentals"
      index="01"
      title="Project Fundamentals"
      sub="What it is, what it claims to solve, and how far that is from everything else already shipped."
      right={
        <Tag tone="ink">
          {project.category} · {project.parameters[0].score}
        </Tag>
      }
    >
      {(seen) => (
        <>
          <div className="bl-fund__lead">
            <p className="eyebrow">What is it?</p>
            <p className="bl-fund__one">{project.oneLiner}</p>
          </div>

          <div className="bl-grid bl-grid--3">
            <Block title="Idea">
              <p className="bl-body">{project.idea}</p>
            </Block>

            <Block title="Uniqueness">
              <div className="bl-meterrow">
                <ArcMeter
                  value={f.uniqueness.score}
                  color={qualityColor[qualityBand(f.uniqueness.score)]}
                  width={148}
                  run={seen}
                />
                <span className="bl-meterrow__v num">{f.uniqueness.score}</span>
              </div>
              <p className="bl-body bl-body--sm">{f.uniqueness.note}</p>
            </Block>

            <Block title="Innovation">
              <div className="bl-meterrow">
                <ArcMeter
                  value={f.innovation.score}
                  color={qualityColor[qualityBand(f.innovation.score)]}
                  width={148}
                  run={seen}
                  delay={120}
                />
                <span className="bl-meterrow__v num">{f.innovation.score}</span>
              </div>
              <p className="bl-body bl-body--sm">{f.innovation.note}</p>
            </Block>
          </div>

          <div className="bl-grid bl-grid--2 bl-grid--tight">
            <Block title="Narrative tags">
              <div className="bl-tags">
                {project.narrative.tags.map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </div>
            </Block>

            <Block title="Key findings">
              <ul className="bl-findings">
                {f.keyFindings.map((k) => (
                  <li key={k.text} className="bl-finding">
                    <span
                      className="bl-finding__dot"
                      style={{ background: signalColor[k.signal] }}
                    />
                    <span className="bl-finding__t">{k.text}</span>
                  </li>
                ))}
              </ul>
            </Block>
          </div>
        </>
      )}
    </Section>
  );
}
