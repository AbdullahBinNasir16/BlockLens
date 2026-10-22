import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { EmptyNote } from '../components/primitives/Bits';
import { Icon } from '../components/app/Icons';
import { findByContract } from '../data/projects';
import { shortAddr } from '../lib/format';
import { OUTCOME_LABEL, fetchHistory, type HistoryEntry, type Outcome } from '../lib/live/product';

/* ============================================================
   History — every address the user opened, held by the API.
   ============================================================ */

type Load<T> = { state: 'loading' } | { state: 'ok'; value: T } | { state: 'error'; msg: string };

const TONE: Record<Outcome, string> = {
  profile: 'var(--pos)',
  tracked: 'var(--ink)',
  live: 'var(--ink-4)',
};

export function HistoryPage() {
  const nav = useNavigate();
  const [items, setItems] = useState<Load<HistoryEntry[]>>({ state: 'loading' });
  const [filter, setFilter] = useState<'all' | Outcome>('all');

  useEffect(() => {
    let alive = true;
    fetchHistory(200)
      .then((h) => alive && setItems({ state: 'ok', value: h }))
      .catch((e) => alive && setItems({ state: 'error', msg: String(e?.message ?? e) }));
    return () => {
      alive = false;
    };
  }, []);

  const all = items.state === 'ok' ? items.value : [];
  const rows = useMemo(() => (filter === 'all' ? all : all.filter((h) => h.outcome === filter)), [all, filter]);
  const grouped = useMemo(() => {
    const map = new Map<string, HistoryEntry[]>();
    rows.forEach((r) => {
      const day = r.opened_at.slice(0, 10);
      map.set(day, [...(map.get(day) ?? []), r]);
    });
    return [...map.entries()];
  }, [rows]);

  const open = (a: string) => {
    const known = findByContract(a);
    nav(known ? `/app/project/${known.project.id}` : `/app/token/${a}`);
  };

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Archive</p>
          <h1 className="display d2">History</h1>
          <p className="bl-page__sub">Every address you investigated, and what it resolved to. Open one to reload it.</p>
        </div>
        <div className="bl-page__headr">
          <span className="meta">{all.length} investigations</span>
        </div>
      </header>

      <div className="bl-filters">
        <div className="bl-filters__grp">
          <span className="eyebrow">Resolved to</span>
          {(['all', 'tracked', 'live', 'profile'] as const).map((s) => (
            <button key={s} className="bl-fchip" data-on={filter === s} onClick={() => setFilter(s)}>
              {s === 'all' ? 'All' : OUTCOME_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      {items.state === 'error' && <EmptyNote title="The BlockLens API is not answering" detail={items.msg} />}
      {items.state === 'ok' && all.length === 0 && (
        <EmptyNote title="No investigations yet" detail="Paste any Base contract on New Investigation and it will be recorded here." />
      )}

      <div className="bl-hist">
        {grouped.map(([date, entries]) => (
          <section key={date} className="bl-histday">
            <div className="bl-histday__h">
              <span className="eyebrow eyebrow-ink">{date}</span>
              <span className="bl-histday__rule" />
              <span className="meta">{entries.length}</span>
            </div>
            {entries.map((h) => {
              const known = findByContract(h.address);
              return (
                <button key={h.id} className="bl-histrow" onClick={() => open(h.address)}>
                  <span className="bl-histrow__time meta">{h.opened_at.slice(11, 16)}</span>
                  <span className="bl-histrow__id">
                    <span className="bl-histrow__n">{known ? known.project.name : shortAddr(h.address, 8, 6)}</span>
                    <span className="meta num">{known ? `$${known.project.ticker}` : h.chain}</span>
                  </span>
                  <span className="bl-histrow__status meta" style={{ color: TONE[h.outcome] }}>
                    ● {OUTCOME_LABEL[h.outcome]}
                  </span>
                  <span className="bl-rowact">
                    Reopen <Icon.Arrow size={13} />
                  </span>
                </button>
              );
            })}
          </section>
        ))}
      </div>
    </div>
  );
}
