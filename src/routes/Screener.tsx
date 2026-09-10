import { useEffect, useMemo, useRef, useState } from 'react';
import type { FunnelStage, ScreenerQuery, WalletMatch } from '../data/types';
import { CHECK_BY_ID } from '../data/checks';
import { chainMeta } from '../data/projects';
import { CORPUS_NOTE, WALLET_CORPUS } from '../data/wallets';
import { emptyQuery, windowRange } from '../data/presets';
import { evaluateQuery } from '../lib/screener';
import { int } from '../lib/format';
import { ProvChip } from '../components/primitives/Bits';
import { FilterPanel, searchableCount } from '../components/screener/FilterPanel';
import { Funnel } from '../components/screener/Funnel';
import { ResultsTable, SORTS, sortValue, type SortKey } from '../components/screener/ResultsTable';
import { WalletBubbles } from '../components/screener/WalletBubbles';
import { WalletDrawer } from '../components/screener/WalletDrawer';

/* ============================================================
   Wallet Screener.

   The page holds two queries: the one being edited and the one last
   searched. Results always belong to the second, so editing a filter never
   quietly changes the rows on screen — it marks them out of date and waits
   for Search. `evaluateQuery` is treated as a black box, which is what lets
   it be swapped for a network call untouched.
   ============================================================ */

type View = 'list' | 'bubbles';

/** One concrete way to loosen the stage that emptied the result set. The
 *  zero state is only useful if it offers the next move, not a diagnosis. */
function relaxation(
  q: ScreenerQuery,
  stage: FunnelStage
): { label: string; apply: () => ScreenerQuery } | null {
  if (stage.id === 'scope') {
    const ytd = windowRange('ytd');
    if (q.scope.from > ytd.from) {
      return {
        label: 'Widen the window to year-to-date',
        apply: () => ({ ...q, scope: { ...q.scope, ...ytd } }),
      };
    }
    return null;
  }

  if (stage.id === 'rule') {
    const rule = q.projectRule;
    if (rule.quantifier === 'atLeast' && rule.count > 1) {
      return {
        label: `Ask for at least ${rule.count - 1} project${rule.count - 1 === 1 ? '' : 's'}`,
        apply: () => ({ ...q, projectRule: { ...rule, count: rule.count - 1 } }),
      };
    }
    const last = rule.checks[rule.checks.length - 1];
    if (last) {
      return {
        label: `Turn off ${CHECK_BY_ID[last.checkId]?.label ?? last.checkId}`,
        apply: () => ({ ...q, projectRule: { ...rule, checks: rule.checks.slice(0, -1) } }),
      };
    }
    return null;
  }

  if (stage.id.startsWith('check:')) {
    const id = stage.id.slice(6);
    return {
      label: `Turn off ${CHECK_BY_ID[id]?.label ?? id}`,
      apply: () => ({ ...q, walletChecks: q.walletChecks.filter((c) => c.checkId !== id) }),
    };
  }

  return null;
}

const same = (a: ScreenerQuery, b: ScreenerQuery) => JSON.stringify(a) === JSON.stringify(b);

export function Screener() {
  const [draft, setDraft] = useState<ScreenerQuery>(() => emptyQuery());
  const [searched, setSearched] = useState<ScreenerQuery | null>(null);
  const [searching, setSearching] = useState(false);
  const [view, setView] = useState<View>('list');
  const [sort, setSort] = useState<SortKey>('realizedPnl');
  const [desc, setDesc] = useState(true);
  const [open, setOpen] = useState<WalletMatch | null>(null);

  const resultsRef = useRef<HTMLElement>(null);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const result = useMemo(
    () => (searched ? evaluateQuery(searched, WALLET_CORPUS) : null),
    [searched]
  );

  const rows = useMemo(() => {
    if (!result) return [];
    const s = [...result.matches].sort((a, b) => sortValue(a, sort) - sortValue(b, sort));
    return desc ? s.reverse() : s;
  }, [result, sort, desc]);

  const stale = searched !== null && !same(draft, searched);

  const search = (q: ScreenerQuery = draft) => {
    if (searchableCount(q) === 0) return;
    setOpen(null);
    setSearching(true);
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    window.clearTimeout(timer.current);
    /* A beat long enough to read as a search, short enough not to be
       theatre. Under reduced motion there is no beat at all. */
    timer.current = window.setTimeout(
      () => {
        setSearched(q);
        setSearching(false);
        resultsRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      },
      reduce ? 0 : 600
    );
  };

  const onSort = (k: SortKey) => {
    if (k === sort) setDesc((d) => !d);
    else {
      setSort(k);
      setDesc(true);
    }
  };

  const relax = result?.limitingStage && searched ? relaxation(searched, result.limitingStage) : null;

  return (
    <div className="bl-page bl-screener">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Cross-project discovery</p>
          <h1 className="display d2">Wallet Screener</h1>
          <p className="bl-page__sub">
            Add the contracts you care about, switch on what a wallet has to have done, and search.
          </p>
        </div>
        <div className="bl-page__headr">
          <ProvChip live={false} note={CORPUS_NOTE} />
        </div>
      </header>

      <FilterPanel query={draft} onChange={setDraft} onSearch={() => search()} searching={searching} />

      <section className="bl-out" ref={resultsRef} data-busy={searching} aria-live="polite">
        {searching && <div className="bl-out__sweep" aria-hidden="true" />}

        {!result ? (
          <div className="bl-idle">
            <svg viewBox="0 0 120 60" width="120" height="60" aria-hidden="true">
              <circle cx="30" cy="34" r="18" fill="none" stroke="var(--rule-strong)" />
              <circle cx="66" cy="26" r="12" fill="none" stroke="var(--rule-strong)" />
              <circle cx="92" cy="38" r="8" fill="none" stroke="var(--rule-strong)" />
            </svg>
            <p className="bl-idle__t">
              {searching ? `Screening ${int(WALLET_CORPUS.length)} wallets…` : 'No search yet.'}
            </p>
            <p className="bl-idle__d meta">
              Choose a chain, add at least one contract, switch on filters, then search. Results
              come back as a list or as bubbles.
            </p>
          </div>
        ) : (
          <>
            <header className="bl-out__head">
              <div className="bl-out__count">
                <span className="eyebrow eyebrow-ink">Results</span>
                <span className="bl-out__n num">{int(result.matches.length)}</span>
                <span className="meta">
                  wallets on {chainMeta[searched!.scope.chain].label}
                </span>
              </div>

              <div className="bl-out__ctl">
                <div className="bl-seg" role="radiogroup" aria-label="View">
                  {(['list', 'bubbles'] as View[]).map((v) => (
                    <button
                      key={v}
                      role="radio"
                      aria-checked={view === v}
                      className="bl-seg__b"
                      data-on={view === v}
                      onClick={() => setView(v)}
                    >
                      {v === 'list' ? 'List' : 'Bubbles'}
                    </button>
                  ))}
                </div>
              </div>
            </header>

            <Funnel stages={result.funnel} />

            {stale && (
              <div className="bl-stale">
                <span>Filters changed since this search — these are the last results.</span>
                <button className="bl-stale__b" onClick={() => search()} disabled={searching}>
                  Search again
                </button>
              </div>
            )}

            {result.matches.length > 0 && (
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
                      onClick={() => {
                        setSort(s.k);
                      }}
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
            )}

            {result.matches.length === 0 ? (
              <div className="bl-zero">
                <p className="bl-zero__t">No wallets passed.</p>
                {result.limitingStage ? (
                  <p className="bl-zero__d">
                    <b>{result.limitingStage.label}</b> removed the last{' '}
                    {int(result.limitingStage.removed)}{' '}
                    {result.limitingStage.removed === 1 ? 'wallet' : 'wallets'}.
                  </p>
                ) : (
                  <p className="bl-zero__d">
                    Nothing traded these contracts inside the window.
                  </p>
                )}
                {relax && (
                  <button
                    className="bl-zero__act"
                    onClick={() => {
                      const next = relax.apply();
                      setDraft(next);
                      search(next);
                    }}
                  >
                    {relax.label} and search again
                  </button>
                )}
              </div>
            ) : view === 'list' ? (
              <ResultsTable rows={rows} sort={sort} desc={desc} onSort={onSort} onOpen={setOpen} />
            ) : (
              <WalletBubbles rows={rows} sort={sort} desc={desc} onOpen={setOpen} />
            )}

            <p className="bl-page__foot meta">
              {int(result.scopedWallets)} of {int(WALLET_CORPUS.length)} wallets traded these
              contracts in the window. {CORPUS_NOTE}
            </p>
          </>
        )}
      </section>

      {searched && <WalletDrawer match={open} query={searched} onClose={() => setOpen(null)} />}
    </div>
  );
}
