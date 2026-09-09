import { useProject } from '../../lib/project-context';
import { Section, Block } from './Section';
import { Heatmap } from '../primitives/Charts';
import { BarScale } from '../primitives/Meters';
import { Tag, KV } from '../primitives/Bits';
import { Icon } from '../app/Icons';
import { int, qualityBand, qualityColor } from '../../lib/format';

const KIND_TONE: Record<string, string> = {
  origin: 'var(--ink-4)',
  build: 'var(--ink)',
  release: 'var(--pos)',
  audit: 'var(--warn)',
  current: 'var(--pos)',
};

export function GithubSection() {
  const { project, github } = useProject();
  return (
    <Section
      id="github"
      index="06"
      title="GitHub Intelligence"
      sub="Whether the code exists, who writes it, and whether the pace survived the token launch."
      right={<Tag tone="positive">Last commit {github.lastCommit}</Tag>}
      wide
    >
      {(seen) => (
        <>
          <div className="bl-repo">
            <div className="bl-repo__id">
              <span className="bl-repo__icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.3">
                  <path d="M8 20v-3.2c0-.9.3-1.5.7-1.9-2.9-.3-5.9-1.4-5.9-6.3 0-1.4.5-2.6 1.3-3.5-.1-.3-.6-1.6.1-3.4 0 0 1.1-.3 3.5 1.3a12 12 0 016.4 0c2.4-1.6 3.5-1.3 3.5-1.3.7 1.8.2 3.1.1 3.4.8.9 1.3 2.1 1.3 3.5 0 4.9-3 6-5.9 6.3.5.4.9 1.2.9 2.4V20" />
                </svg>
              </span>
              <div>
                <a
                  className="bl-repo__name"
                  href={github.url}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {github.repo} <Icon.Ext size={13} />
                </a>
                <p className="bl-body bl-body--sm">{github.description}</p>
              </div>
            </div>
            <div className="bl-repo__stats">
              {[
                { k: 'Stars', v: int(github.stars) },
                { k: 'Forks', v: int(github.forks) },
                { k: 'Contributors', v: github.contributors },
                { k: 'Commits', v: int(github.commits) },
                { k: 'Open issues', v: github.openIssues },
                { k: 'Licence', v: github.license },
              ].map((s) => (
                <div key={s.k} className="bl-fact">
                  <span className="bl-fact__k eyebrow">{s.k}</span>
                  <span className="bl-fact__v num">{s.v}</span>
                </div>
              ))}
            </div>
          </div>

          <Block
            title="Contribution activity"
            note={`Last 53 weeks · repository created ${github.createdAt}`}
          >
            <Heatmap weeks={github.heatmap} run={seen} />
          </Block>

          <div className="bl-grid bl-grid--3">
            <Block title="Development timeline">
              <ol className="bl-gtimeline">
                {github.timeline.map((t, i) => (
                  <li key={t.label} className="bl-gt">
                    <span className="bl-gt__rail" aria-hidden="true">
                      <span
                        className="bl-gt__node"
                        style={{
                          background: KIND_TONE[t.kind],
                          transform: seen ? 'scale(1)' : 'scale(0)',
                          transitionDelay: `${i * 60}ms`,
                        }}
                      />
                    </span>
                    <span className="bl-gt__b">
                      <span className="bl-gt__d meta">{t.date}</span>
                      <span className="bl-gt__l">{t.label}</span>
                      <span className="meta">{t.detail}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </Block>

            <Block title="Contributors" note="Commit share">
              <ul className="bl-contribs">
                {github.topContributors.map((c, i) => (
                  <li key={c.user} className="bl-contrib">
                    <span className="bl-contrib__u">
                      {c.user}
                      {c.linked && (
                        <span className="bl-contrib__link meta" title="Linked to an on-chain identity">
                          ↔
                        </span>
                      )}
                    </span>
                    {/* scaled against the top contributor, so the bar never overruns */}
                    <BarScale
                      value={(c.share / (github.topContributors[0]?.share || 1)) * 100}
                      color={i === 0 ? 'var(--ink)' : 'var(--ink-4)'}
                      height={3}
                      run={seen}
                      delay={i * 50}
                    />
                    <span className="num bl-contrib__v">{c.share}%</span>
                  </li>
                ))}
              </ul>
              <p className="bl-body bl-body--sm">
                Top contributor writes {github.topContributors[0]?.share}% of commits across{' '}
                {github.contributors} contributor{github.contributors === 1 ? '' : 's'}.
              </p>
            </Block>

            <Block title="Development consistency">
              <ul className="bl-consist">
                {github.consistency.map((c, i) => (
                  <li key={c.label} className="bl-consistrow">
                    <span className="bl-consistrow__t">
                      <span className="bl-consistrow__l">{c.label}</span>
                      <span
                        className="num bl-consistrow__v"
                        style={{ color: qualityColor[qualityBand(c.value)] }}
                      >
                        {c.value}
                      </span>
                    </span>
                    <BarScale
                      value={c.value}
                      color={qualityColor[qualityBand(c.value)]}
                      height={3}
                      run={seen}
                      delay={i * 60}
                    />
                    <span className="meta">{c.note}</span>
                  </li>
                ))}
              </ul>
              <div className="bl-langs">
                {github.languages.map((l) => (
                  <KV key={l.name} k={l.name} v={`${l.pct}%`} />
                ))}
              </div>
            </Block>
          </div>

          {(() => {
            const activity =
              github.consistency.find((c) => c.label === 'Post-launch activity')?.value ?? 100;
            const stale = activity < 50;
            return (
              <div className="bl-callout" data-tone={stale ? 'neg' : 'pos'}>
                <span className="bl-callout__m">{stale ? '!' : '✓'}</span>
                <div>
                  <p className="bl-callout__t">
                    {stale
                      ? 'The public repositories have gone quiet'
                      : 'Development is current and open'}
                  </p>
                  <p className="bl-callout__d">
                    {stale ? (
                      <>
                        {github.repo} was opened {github.createdAt} and last pushed{' '}
                        {github.lastCommit}, with {github.forks} fork
                        {github.forks === 1 ? '' : 's'}. The hosted product may still be under active
                        development — but none of that work is visible in public.
                      </>
                    ) : (
                      <>
                        {int(github.stars)} stars, {int(github.forks)} forks and{' '}
                        {github.contributors} contributors on {github.repo}, opened{' '}
                        {github.createdAt} and pushed {github.lastCommit}. The repository predates
                        the {project.ticker} pair, which opened {project.deployedAt}.
                      </>
                    )}
                  </p>
                </div>
              </div>
            );
          })()}
        </>
      )}
    </Section>
  );
}
