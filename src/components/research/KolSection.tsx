import { Link } from 'react-router-dom';
import { Section } from './Section';
import { MiniRing } from '../primitives/Meters';
import { XAvatar } from '../primitives/XAvatar';
import { useProject } from '../../lib/project-context';
import { qualityBand, qualityColor } from '../../lib/format';

export function KolSection() {
  const { kols } = useProject();
  const ranked = [...kols].sort((a, b) => b.winRate - a.winRate);

  return (
    <Section
      id="kols"
      index="05"
      title="KOL Backing"
      sub="Accounts that have covered this project, with their historical record."
      wide
      right={
        <Link to="/app/kols" className="bl-textbtn">
          All KOLs →
        </Link>
      }
    >
      {(seen) => (
        <>
          <ul className="bl-kolgrid">
            {ranked.map((k, i) => {
              const band = qualityBand(k.winRate);
              const up = k.avgOutcome >= 0;
              return (
                <li key={k.id} className="bl-kolcard">
                  <a
                    className="bl-kolcard__id"
                    href={`https://x.com/${k.handle}`}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    <XAvatar handle={k.handle} size={52} />
                    <span className="bl-kolcard__handle">@{k.handle}</span>
                  </a>

                  <span className="bl-kolcard__score">
                    <MiniRing
                      value={k.winRate}
                      color={qualityColor[band]}
                      size={62}
                      stroke={4}
                      run={seen}
                      delay={i * 70}
                    >
                      <span style={{ fontSize: 15 }}>{k.winRate}</span>
                    </MiniRing>
                    <span className="eyebrow">Score</span>
                  </span>

                  <span className="bl-kolcard__outcome">
                    <span
                      className="bl-kolcard__v num"
                      style={{ color: up ? 'var(--pos)' : 'var(--neg)' }}
                    >
                      {up ? '+' : ''}
                      {k.avgOutcome}%
                    </span>
                    <span className="eyebrow">Outcome</span>
                  </span>
                </li>
              );
            })}
          </ul>

          <p className="meta bl-kolnote">
            Accounts and profile images are real. The score and outcome beside each one are
            prototype sample values — no promotion record has been measured for this build.
          </p>
        </>
      )}
    </Section>
  );
}
