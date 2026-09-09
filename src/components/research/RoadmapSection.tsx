import { useState } from 'react';
import { Section } from './Section';
import { Tag } from '../primitives/Bits';
import { useProject } from '../../lib/project-context';
import type { RoadmapStatus } from '../../data/types';

const STATUS: Record<RoadmapStatus, { label: string; color: string; mark: string }> = {
  done: { label: 'Delivered', color: 'var(--pos)', mark: '✓' },
  active: { label: 'In progress', color: 'var(--warn)', mark: '●' },
  missed: { label: 'Missed', color: 'var(--neg)', mark: '×' },
  planned: { label: 'Planned', color: 'var(--ink-4)', mark: '○' },
};

const ORDER: RoadmapStatus[] = ['done', 'active', 'missed', 'planned'];

export function RoadmapSection() {
  const { roadmap } = useProject();
  const [filter, setFilter] = useState<RoadmapStatus | 'all'>('all');

  const counts = ORDER.reduce<Record<string, number>>((a, s) => {
    a[s] = roadmap.filter((r) => r.status === s).length;
    return a;
  }, {});

  const rows = filter === 'all' ? roadmap : roadmap.filter((r) => r.status === filter);
  const delivered = counts.done ?? 0;

  return (
    <Section
      id="roadmap"
      index="08"
      title="Roadmap"
      sub="What was promised, what landed, and what slipped."
      right={
        <Tag tone={delivered > roadmap.length / 2 ? 'positive' : 'warn'}>
          {delivered} of {roadmap.length} delivered
        </Tag>
      }
      wide
    >
      {(seen) => (
        <>
          {/* one bar showing the whole programme at a glance */}
          <div className="bl-rmbar">
            {ORDER.filter((s) => counts[s] > 0).map((s, i) => (
              <span
                key={s}
                className="bl-rmbar__seg"
                data-on={filter === 'all' || filter === s}
                style={{
                  flexBasis: seen ? `${(counts[s] / roadmap.length) * 100}%` : '0%',
                  background: STATUS[s].color,
                  transitionDelay: `${i * 90}ms`,
                }}
                title={`${counts[s]} ${STATUS[s].label.toLowerCase()}`}
              />
            ))}
          </div>

          <div className="bl-rmkey">
            <button
              className="bl-rmkey__b"
              data-on={filter === 'all'}
              onClick={() => setFilter('all')}
            >
              <span className="bl-rmkey__dot" style={{ background: 'var(--ink)' }} />
              All {roadmap.length}
            </button>
            {ORDER.filter((s) => counts[s] > 0).map((s) => (
              <button
                key={s}
                className="bl-rmkey__b"
                data-on={filter === s}
                onClick={() => setFilter(filter === s ? 'all' : s)}
              >
                <span className="bl-rmkey__dot" style={{ background: STATUS[s].color }} />
                {STATUS[s].label} {counts[s]}
              </button>
            ))}
          </div>

          <ol className="bl-rm">
            {rows.map((r, i) => (
              <li key={r.label} className="bl-rmitem" data-status={r.status}>
                <span className="bl-rmitem__date num">{r.date}</span>
                <span className="bl-rmitem__rail" aria-hidden="true">
                  <span
                    className="bl-rmitem__node"
                    style={{
                      background: r.status === 'planned' ? 'var(--paper)' : STATUS[r.status].color,
                      borderColor: STATUS[r.status].color,
                      transform: seen ? 'scale(1)' : 'scale(0)',
                      transitionDelay: `${Math.min(i, 12) * 45}ms`,
                    }}
                  />
                </span>
                <span className="bl-rmitem__b">
                  <span className="bl-rmitem__l">{r.label}</span>
                  <span className="bl-rmitem__d">{r.detail}</span>
                </span>
                <span className="bl-rmitem__track meta">{r.track}</span>
                <span
                  className="bl-rmitem__status"
                  style={{ color: STATUS[r.status].color }}
                  title={STATUS[r.status].label}
                >
                  {STATUS[r.status].mark}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
    </Section>
  );
}
