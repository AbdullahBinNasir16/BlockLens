import { useProject } from '../../lib/project-context';
import { Section, Block } from './Section';
import { AreaChart } from '../primitives/Charts';
import { XAvatar } from '../primitives/XAvatar';
import { compact, int, pct } from '../../lib/format';

export function SocialSection() {
  const { social } = useProject();
  const maxReach = Math.max(...social.topAccounts.map((a) => a.followers));
  const maxDelta = Math.max(...social.momentum.map((m) => Math.abs(m.delta)), 1);

  return (
    <Section
      id="social"
      index="07"
      title="Social Intelligence"
      sub="Reach, attention and who is carrying the conversation."
      wide
    >
      {(seen) => (
        <>
          {/* headline numbers, no prose */}
          <div className="bl-factstrip">
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Followers</span>
              <span className="bl-fact__v num">{compact(social.followers)}</span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">7d</span>
              <span className="bl-fact__v num" style={{ color: 'var(--pos)' }}>
                {pct(social.followersChange7d)}
              </span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Posts · 30d</span>
              <span className="bl-fact__v num">{social.posts30d}</span>
            </div>
            <div className="bl-fact">
              <span className="bl-fact__k eyebrow">Engagement</span>
              <span className="bl-fact__v num">{social.avgEngagement}%</span>
            </div>
          </div>

          <div className="bl-grid bl-grid--2">
            <Block title="Follower growth">
              <AreaChart
                data={social.growth}
                height={180}
                run={seen}
                color="var(--ink)"
                valueFormat={(v) => int(v)}
              />
            </Block>

            <Block title="Mention activity">
              <AreaChart
                data={social.mentions}
                height={180}
                run={seen}
                color="var(--ink-3)"
                valueFormat={(v) => int(v)}
              />
            </Block>
          </div>

          <div className="bl-grid bl-grid--split">
            <Block title="Accounts in the conversation" note="Bar length is audience size">
              <ul className="bl-reach">
                {[...social.topAccounts]
                  .sort((a, b) => b.followers - a.followers)
                  .map((a, i) => (
                    <li key={a.handle} className="bl-reachrow">
                      <a
                        className="bl-reachrow__h"
                        href={`https://x.com/${a.handle}`}
                        target="_blank"
                        rel="noreferrer noopener"
                      >
                        <XAvatar handle={a.handle} size={26} />
                        <span className="bl-reachrow__n">@{a.handle}</span>
                      </a>
                      <span className="bl-reachrow__track">
                        <span
                          className="bl-reachrow__bar"
                          style={{
                            width: seen ? `${(a.followers / maxReach) * 100}%` : 0,
                            background: a.kind === 'Official' ? 'var(--ink)' : 'var(--ink-4)',
                            transitionDelay: `${i * 60}ms`,
                          }}
                        />
                      </span>
                      <span className="bl-reachrow__v num">{compact(a.followers)}</span>
                    </li>
                  ))}
              </ul>
            </Block>

            <Block title="Momentum" note="Change against the previous 7 days">
              <ul className="bl-mom">
                {social.momentum.map((m, i) => {
                  const up = m.delta >= 0;
                  return (
                    <li key={m.label} className="bl-momrow">
                      <span className="bl-momrow__l">{m.label}</span>
                      <span className="bl-momrow__axis">
                        <span className="bl-momrow__zero" />
                        <span
                          className="bl-momrow__bar"
                          data-up={up}
                          style={{
                            width: seen ? `${(Math.abs(m.delta) / maxDelta) * 46}%` : 0,
                            transitionDelay: `${i * 70}ms`,
                          }}
                        />
                      </span>
                      <span
                        className="bl-momrow__v num"
                        style={{ color: up ? 'var(--pos)' : 'var(--neg)' }}
                      >
                        {up ? '+' : ''}
                        {m.delta}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Block>
          </div>
        </>
      )}
    </Section>
  );
}
