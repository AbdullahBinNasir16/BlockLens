import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { history } from '../data/lists';
import { TokenMark, ChainDot } from '../components/primitives/TokenMark';
import { DotScale } from '../components/primitives/Meters';
import { Icon } from '../components/app/Icons';
import { bandColor } from '../lib/format';

const STATUS_TONE: Record<string, string> = {
  complete: 'var(--pos)',
  partial: 'var(--warn)',
  stale: 'var(--ink-4)',
};

export function HistoryPage() {
  const nav = useNavigate();
  const [filter, setFilter] = useState('all');

  const rows = useMemo(
    () => (filter === 'all' ? history : history.filter((h) => h.status === filter)),
    [filter]
  );

  const grouped = useMemo(() => {
    const map = new Map<string, typeof rows>();
    rows.forEach((r) => {
      const arr = map.get(r.date) ?? [];
      arr.push(r);
      map.set(r.date, arr);
    });
    return [...map.entries()];
  }, [rows]);

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Archive</p>
          <h1 className="display d2">Research History</h1>
          <p className="bl-page__sub">Every investigation you have run. Open one to reload it.</p>
        </div>
        <div className="bl-page__headr">
          <span className="meta">{history.length} investigations</span>
        </div>
      </header>

      <div className="bl-filters">
        <div className="bl-filters__grp">
          <span className="eyebrow">Status</span>
          {['all', 'complete', 'partial', 'stale'].map((s) => (
            <button key={s} className="bl-fchip" data-on={filter === s} onClick={() => setFilter(s)}>
              {s[0].toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="bl-hist">
        {grouped.map(([date, items]) => (
          <section key={date} className="bl-histday">
            <div className="bl-histday__h">
              <span className="eyebrow eyebrow-ink">{date}</span>
              <span className="bl-histday__rule" />
              <span className="meta">{items.length}</span>
            </div>

            {items.map((h) => (
              <button
                key={h.id + h.time}
                className="bl-histrow"
                onClick={() => nav(`/app/project/${h.id}`)}
              >
                <span className="bl-histrow__time meta">{h.time}</span>
                <TokenMark
                  logo={h.logo}
                  monogram={h.monogram}
                  chain={h.chain}
                  size={34}
                  chainBadge
                />
                <span className="bl-histrow__id">
                  <span className="bl-histrow__n">{h.name}</span>
                  <span className="meta">${h.ticker}</span>
                </span>
                <ChainDot chain={h.chain} />
                <span className="bl-tag" data-size="sm">
                  {h.category}
                </span>

                <span className="bl-histrow__score">
                  <span className="meta">Risk</span>
                  <span className="num" style={{ color: bandColor[h.riskLevel] }}>
                    {h.risk}
                  </span>
                  <DotScale value={h.risk} color={bandColor[h.riskLevel]} count={10} dot={5} />
                </span>

                <span className="bl-histrow__score">
                  <span className="meta">Confidence</span>
                  <span className="num">{h.confidence}</span>
                </span>

                <span className="bl-histrow__status meta" style={{ color: STATUS_TONE[h.status] }}>
                  ● {h.status}
                </span>

                <span className="bl-rowact">
                  Reopen <Icon.Arrow size={13} />
                </span>
              </button>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
