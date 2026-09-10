import { useEffect, useMemo, useState } from 'react';
import type { Chain, KolFocus, KolProfile, Project } from '../data/types';
import { FOCUS_ORDER, KOLS, KOL_NOTE } from '../data/kols';
import { CHAINS, chainMeta, datasets } from '../data/projects';
import { ProvChip } from '../components/primitives/Bits';
import { Icon } from '../components/app/Icons';
import { KolCard, type KolSortKey } from '../components/kols/KolCard';
import { KolMap } from '../components/kols/KolMap';
import { RangeFilter, linear, logScale } from '../components/kols/RangeFilter';
import { compact } from '../lib/format';

/* ============================================================
   KOL directory.

   Every tracked account, filterable by reach, record and how often they
   write their reasoning down. Filters apply as they move — there are two
   dozen accounts, not four hundred wallets, so there is nothing to wait
   for and no Search button to press.
   ============================================================ */

interface Filters {
  q: string;
  followers: number;
  social: number;
  winRate: number;
  thesis: number;
  outcome: number;
  focus: KolFocus[];
  chains: Chain[];
}

const OUTCOME_FLOOR = -40;

const EMPTY: Filters = {
  q: '',
  followers: 0,
  social: 0,
  winRate: 0,
  thesis: 0,
  outcome: OUTCOME_FLOOR,
  focus: [],
  chains: [],
};

const FOLLOWERS = logScale(10_000, 1_000_000);
const PCT = linear(0, 100);
const OUTCOME = linear(OUTCOME_FLOOR, 160, 5);

const signedPct = (v: number) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v)}%`;

/* Each filter as a rule that knows whether it is on, how to test an
   account, how to switch itself off and how to name itself. Kept as one
   list so the active-filter pills and the empty state can both ask every
   rule the same questions. Different rules combine with AND; choices
   inside one rule — two focus tags, two chains — combine with OR. */
interface Rule {
  id: string;
  on: (f: Filters) => boolean;
  label: (f: Filters) => string;
  test: (k: KolProfile, f: Filters) => boolean;
  off: (f: Filters) => Filters;
}

const RULES: Rule[] = [
  {
    id: 'q',
    on: (f) => f.q.trim() !== '',
    label: (f) => `“${f.q.trim()}”`,
    test: (k, f) => {
      const n = f.q.trim().toLowerCase().replace(/^@/, '');
      return k.handle.toLowerCase().includes(n) || k.name.toLowerCase().includes(n);
    },
    off: (f) => ({ ...f, q: '' }),
  },
  {
    id: 'followers',
    on: (f) => f.followers > 0,
    label: (f) => `Followers ≥ ${compact(f.followers)}`,
    test: (k, f) => k.followers >= f.followers,
    off: (f) => ({ ...f, followers: 0 }),
  },
  {
    id: 'social',
    on: (f) => f.social > 0,
    label: (f) => `Social ≥ ${f.social}`,
    test: (k, f) => k.socialScore >= f.social,
    off: (f) => ({ ...f, social: 0 }),
  },
  {
    id: 'winRate',
    on: (f) => f.winRate > 0,
    label: (f) => `Win rate ≥ ${f.winRate}%`,
    test: (k, f) => k.winRate >= f.winRate,
    off: (f) => ({ ...f, winRate: 0 }),
  },
  {
    id: 'thesis',
    on: (f) => f.thesis > 0,
    label: (f) => `Thesis ≥ ${f.thesis}`,
    test: (k, f) => k.thesisScore >= f.thesis,
    off: (f) => ({ ...f, thesis: 0 }),
  },
  {
    id: 'outcome',
    on: (f) => f.outcome > OUTCOME_FLOOR,
    label: (f) => `Outcome ≥ ${signedPct(f.outcome)}`,
    test: (k, f) => k.avgOutcome >= f.outcome,
    off: (f) => ({ ...f, outcome: OUTCOME_FLOOR }),
  },
  {
    id: 'focus',
    on: (f) => f.focus.length > 0,
    label: (f) => f.focus.join(' or '),
    test: (k, f) => f.focus.some((x) => k.focus.includes(x)),
    off: (f) => ({ ...f, focus: [] }),
  },
  {
    id: 'chains',
    on: (f) => f.chains.length > 0,
    label: (f) => f.chains.map((c) => chainMeta[c].label).join(' or '),
    test: (k, f) => f.chains.some((c) => k.chains.includes(c)),
    off: (f) => ({ ...f, chains: [] }),
  },
];

const passesAll = (k: KolProfile, f: Filters, skip?: string) =>
  RULES.every((r) => r.id === skip || !r.on(f) || r.test(k, f));

const SORTS: { k: KolSortKey; label: string }[] = [
  { k: 'followers', label: 'Followers' },
  { k: 'socialScore', label: 'Social' },
  { k: 'winRate', label: 'Win rate' },
  { k: 'thesisScore', label: 'Thesis' },
  { k: 'avgOutcome', label: 'Outcome' },
  { k: 'calls', label: 'Calls' },
];

/** Which indexed projects each account covered — read from the project
 *  records, so the directory never claims coverage a project page lacks. */
const COVERED: Record<string, Project[]> = Object.fromEntries(
  KOLS.map((k) => [
    k.id,
    Object.values(datasets)
      .filter((d) => d.kols.some((x) => x.handle === k.handle))
      .map((d) => d.project),
  ])
);

const toggle = <T,>(xs: T[], x: T) => (xs.includes(x) ? xs.filter((v) => v !== x) : [...xs, x]);

type View = 'cards' | 'map';

export function Kols() {
  const [f, setF] = useState<Filters>(EMPTY);
  const [sort, setSort] = useState<KolSortKey>('followers');
  const [desc, setDesc] = useState(true);
  const [view, setView] = useState<View>('cards');
  const set = (patch: Partial<Filters>) => setF((prev) => ({ ...prev, ...patch }));

  /* meters grow in once, on arrival */
  const [run, setRun] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setRun(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const shown = useMemo(() => {
    const s = KOLS.filter((k) => passesAll(k, f)).sort((a, b) => a[sort] - b[sort]);
    return desc ? s.reverse() : s;
  }, [f, sort, desc]);

  const active = RULES.filter((r) => r.on(f));

  /* In the empty state, the useful question is which one filter is
     costing the most — so ask each active rule what dropping it returns. */
  const relief = useMemo(() => {
    if (shown.length) return null;
    let best: { rule: Rule; n: number } | null = null;
    for (const r of RULES.filter((x) => x.on(f))) {
      const n = KOLS.filter((k) => passesAll(k, f, r.id)).length;
      if (n > 0 && (!best || n > best.n)) best = { rule: r, n };
    }
    return best;
  }, [f, shown.length]);

  return (
    <div className="bl-page bl-kdir">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Directory</p>
          <h1 className="display d2">KOLs</h1>
          <p className="bl-page__sub">
            Every account BlockLens tracks. Filter by reach, by record, and by how often they write
            their reasoning down.
          </p>
          {/* real faces beside follower counts read as fact, so the caveat
              sits up here rather than only in the footer */}
          <p className="bl-kdir__note meta">
            <span className="bl-src" data-on="false" /> Real accounts, sample numbers — nothing
            here measures these people.
          </p>
        </div>
        <div className="bl-page__headr">
          <ProvChip live={false} note={KOL_NOTE} />
        </div>
      </header>

      <section className="bl-kf" aria-label="Filter KOLs">
        <div className="bl-kf__top">
          <label className="bl-ksearch">
            <Icon.Search size={15} />
            <input
              className="bl-ksearch__in"
              value={f.q}
              placeholder="Search name or @handle"
              onChange={(e) => set({ q: e.target.value })}
              aria-label="Search KOLs"
            />
            {f.q && (
              <button className="bl-ksearch__x" onClick={() => set({ q: '' })} aria-label="Clear search">
                ×
              </button>
            )}
          </label>

          <div className="bl-kf__grp">
            <span className="bl-kf__l">Focus</span>
            {FOCUS_ORDER.map((x) => (
              <button
                key={x}
                className="bl-kchip"
                data-on={f.focus.includes(x)}
                aria-pressed={f.focus.includes(x)}
                onClick={() => set({ focus: toggle(f.focus, x) })}
              >
                {x}
              </button>
            ))}
          </div>

          <div className="bl-kf__grp">
            <span className="bl-kf__l">Chain</span>
            {CHAINS.map((c) => (
              <button
                key={c}
                className="bl-kchip bl-kchip--chain"
                data-on={f.chains.includes(c)}
                aria-pressed={f.chains.includes(c)}
                onClick={() => set({ chains: toggle(f.chains, c) })}
              >
                <img src={chainMeta[c].logo} alt="" width={14} height={14} loading="lazy" />
                {chainMeta[c].short}
              </button>
            ))}
          </div>
        </div>

        <div className="bl-kf__ranges">
          <RangeFilter
            label="Followers"
            value={f.followers}
            floor={0}
            scale={FOLLOWERS}
            format={compact}
            marks={KOLS.map((k) => k.followers)}
            onChange={(v) => set({ followers: v })}
          />
          <RangeFilter
            label="Social score"
            value={f.social}
            floor={0}
            scale={PCT}
            format={String}
            marks={KOLS.map((k) => k.socialScore)}
            onChange={(v) => set({ social: v })}
          />
          <RangeFilter
            label="Win rate"
            value={f.winRate}
            floor={0}
            scale={PCT}
            format={(v) => `${v}%`}
            marks={KOLS.map((k) => k.winRate)}
            onChange={(v) => set({ winRate: v })}
          />
          <RangeFilter
            label="Thesis writing"
            value={f.thesis}
            floor={0}
            scale={PCT}
            format={String}
            marks={KOLS.map((k) => k.thesisScore)}
            onChange={(v) => set({ thesis: v })}
          />
          <RangeFilter
            label="Outcome"
            value={f.outcome}
            floor={OUTCOME_FLOOR}
            scale={OUTCOME}
            format={signedPct}
            marks={KOLS.map((k) => k.avgOutcome)}
            onChange={(v) => set({ outcome: v })}
          />
        </div>
      </section>

      <section className="bl-kr">
        <header className="bl-kr__head">
          <div className="bl-kr__count">
            <span className="bl-kr__n num">{shown.length}</span>
            <span className="meta">of {KOLS.length} accounts</span>
          </div>

          {active.length > 0 && (
            <div className="bl-kr__active">
              {active.map((r) => (
                <button
                  key={r.id}
                  className="bl-kpill"
                  onClick={() => setF(r.off(f))}
                  aria-label={`Remove filter: ${r.label(f)}`}
                >
                  {r.label(f)}
                  <span aria-hidden="true">×</span>
                </button>
              ))}
              <button className="bl-textbtn bl-textbtn--quiet" onClick={() => setF(EMPTY)}>
                Reset all
              </button>
            </div>
          )}

          <div className="bl-seg" role="radiogroup" aria-label="View">
            {(['cards', 'map'] as View[]).map((v) => (
              <button
                key={v}
                role="radio"
                aria-checked={view === v}
                className="bl-seg__b"
                data-on={view === v}
                onClick={() => setView(v)}
              >
                {v === 'cards' ? 'Cards' : 'Map'}
              </button>
            ))}
          </div>
        </header>

        {view === 'map' ? (
          <KolMap
            kols={KOLS}
            passes={(k) => passesAll(k, f)}
            minWin={f.winRate}
            minThesis={f.thesis}
          />
        ) : shown.length === 0 ? (
          <div className="bl-zero">
            <p className="bl-zero__t">No account passes all of these.</p>
            {relief ? (
              <>
                <p className="bl-zero__d">
                  Dropping <b>{relief.rule.label(f)}</b> would bring back {relief.n}{' '}
                  {relief.n === 1 ? 'account' : 'accounts'}.
                </p>
                <button className="bl-zero__act" onClick={() => setF(relief.rule.off(f))}>
                  Drop {relief.rule.label(f)}
                </button>
              </>
            ) : (
              <button className="bl-zero__act" onClick={() => setF(EMPTY)}>
                Reset all filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="bl-sortbar">
              <span className="meta bl-sortbar__l">Sort by</span>
              <div className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Sort by">
                {SORTS.map((s) => (
                  <button
                    key={s.k}
                    role="radio"
                    aria-checked={sort === s.k}
                    className="bl-seg__b"
                    data-on={sort === s.k}
                    onClick={() => setSort(s.k)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <button
                className="bl-dir"
                onClick={() => setDesc((d) => !d)}
                aria-label={desc ? 'Descending — switch to ascending' : 'Ascending — switch to descending'}
              >
                <svg viewBox="0 0 20 20" width="14" height="14" aria-hidden="true" data-desc={desc}>
                  <path d="M10 4v12M5.5 11.5L10 16l4.5-4.5" stroke="currentColor" strokeWidth="1.6" fill="none" />
                </svg>
                {desc ? 'Descending' : 'Ascending'}
              </button>
            </div>

            <div className="bl-kgrid">
              {shown.map((k, i) => (
                <KolCard key={k.id} kol={k} rank={i + 1} sort={sort} covered={COVERED[k.id]} run={run} />
              ))}
            </div>
          </>
        )}

        <p className="bl-page__foot meta">{KOL_NOTE}</p>
      </section>
    </div>
  );
}
