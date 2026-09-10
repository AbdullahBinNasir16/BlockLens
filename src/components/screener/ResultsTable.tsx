import { useLayoutEffect, useRef, useState } from 'react';
import type { WalletMatch } from '../../data/types';
import { datasets } from '../../data/projects';
import { TokenMark } from '../primitives/TokenMark';
import { Icon } from '../app/Icons';
import { useCopy } from '../../lib/hooks';
import { dateShort, duration, int, shortAddr, signedUsd } from '../../lib/format';

/* Rows are a fixed height so the list can be windowed without measuring
   anything. 400 wallets is small, but the same table has to stay honest
   about a corpus that isn't — so it renders a slice, not the whole set. */
const ROW_H = 52;
const OVERSCAN = 8;
/** Below this, windowing costs more than it saves. */
const VIRTUALISE_ABOVE = 80;

export type SortKey = 'realizedPnl' | 'winRate' | 'avgHoldingTime' | 'matched' | 'lastActive';

export const SORTS: { k: SortKey; label: string }[] = [
  { k: 'realizedPnl', label: 'PnL' },
  { k: 'winRate', label: 'Win rate' },
  { k: 'avgHoldingTime', label: 'Avg hold' },
  { k: 'matched', label: 'Projects' },
  { k: 'lastActive', label: 'Last active' },
];

export function sortValue(m: WalletMatch, k: SortKey): number {
  if (k === 'matched') return m.matchedProjects.length;
  return m[k];
}

function AddressCell({ address }: { address: string }) {
  const [copied, copy] = useCopy();
  return (
    <span className="bl-addr">
      <span className="bl-addr__t num">{shortAddr(address, 8, 6)}</span>
      <button
        className="bl-addr__c"
        title={copied ? 'Copied' : `Copy ${address}`}
        aria-label={`Copy address ${address}`}
        onClick={(e) => {
          e.stopPropagation();
          copy(address);
        }}
      >
        {copied ? <Icon.Check size={12} /> : <Icon.Copy size={12} />}
      </button>
    </span>
  );
}

const COLUMNS: { k: SortKey; label: string; align: 'r' | 'l' }[] = [
  { k: 'realizedPnl', label: 'Realized PnL', align: 'r' },
  { k: 'winRate', label: 'Win rate', align: 'r' },
  { k: 'matched', label: 'Projects', align: 'l' },
  { k: 'avgHoldingTime', label: 'Avg hold', align: 'r' },
  { k: 'lastActive', label: 'Last active', align: 'r' },
];

export function ResultsTable({
  rows,
  sort,
  desc,
  onSort,
  onOpen,
}: {
  /** already sorted — the sort is shared with the bubble view */
  rows: WalletMatch[];
  sort: SortKey;
  desc: boolean;
  onSort: (k: SortKey) => void;
  onOpen: (m: WalletMatch) => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewport, setViewport] = useState(600);

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const measure = () => setViewport(el.clientHeight);
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /* a new sort or a new search starts at the top */
  useLayoutEffect(() => {
    scroller.current?.scrollTo(0, 0);
    setScrollTop(0);
  }, [rows]);

  const windowed = rows.length > VIRTUALISE_ABOVE;
  const start = windowed ? Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN) : 0;
  const end = windowed
    ? Math.min(rows.length, Math.ceil((scrollTop + viewport) / ROW_H) + OVERSCAN)
    : rows.length;
  const slice = rows.slice(start, end);

  /* an empty <tr> can collapse to nothing, so the spacer carries a cell */
  const spacer = (h: number, key: string) => (
    <tr key={key} aria-hidden="true">
      <td colSpan={9} style={{ height: h, padding: 0, border: 0 }} />
    </tr>
  );

  return (
    <div className="bl-resultswrap">
      <div
        className="bl-results"
        ref={scroller}
        onScroll={(e) => windowed && setScrollTop(e.currentTarget.scrollTop)}
      >
        <table className="bl-table bl-table--screener">
          <thead>
            <tr>
              <th className="bl-th--n">#</th>
              <th>Wallet</th>
              <th className="bl-th--label">Label</th>
              {COLUMNS.map((c) => (
                <th
                  key={c.k}
                  className={c.align === 'r' ? 'bl-th--r' : undefined}
                  aria-sort={sort === c.k ? (desc ? 'descending' : 'ascending') : 'none'}
                >
                  <button className="bl-sorth" data-on={sort === c.k} onClick={() => onSort(c.k)}>
                    {c.label}
                    {/* only the active column carries a caret — an indicator on
                        every header is decoration, not information */}
                    <span className="bl-sorth__a" aria-hidden="true">
                      {sort === c.k ? (desc ? '▾' : '▴') : ''}
                    </span>
                  </button>
                </th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {start > 0 && spacer(start * ROW_H, 'top')}

            {slice.map((m, i) => {
              const marks = [...new Set(m.matchedProjects)];
              return (
                <tr key={m.wallet.address} className="bl-tr" onClick={() => onOpen(m)}>
                  <td className="bl-td--n meta">{String(start + i + 1).padStart(3, '0')}</td>
                  <td>
                    <AddressCell address={m.wallet.address} />
                  </td>
                  <td className="bl-td--label">
                    {m.wallet.ens ? (
                      <span className="num bl-ens">{m.wallet.ens}</span>
                    ) : m.wallet.label ? (
                      <span className="bl-tag" data-size="sm">
                        {m.wallet.label}
                      </span>
                    ) : (
                      <span className="meta bl-dash">—</span>
                    )}
                  </td>
                  <td
                    className="bl-td--r num"
                    style={{ color: m.realizedPnl >= 0 ? 'var(--pos)' : 'var(--neg)' }}
                  >
                    {signedUsd(m.realizedPnl)}
                  </td>
                  <td className="bl-td--r num">{m.winRate.toFixed(0)}%</td>
                  <td>
                    <span className="bl-matched">
                      {marks.map((id) => {
                        const p = datasets[id]?.project;
                        if (!p) return null;
                        return (
                          <TokenMark key={id} logo={p.logo} monogram={p.monogram} size={20} radius={6} />
                        );
                      })}
                      <span
                        className="meta bl-matched__n"
                        title={`Matched ${marks.length} of ${m.projectsTraded} projects traded in scope`}
                      >
                        {marks.length}/{m.projectsTraded}
                      </span>
                    </span>
                  </td>
                  <td className="bl-td--r num">{duration(m.avgHoldingTime)}</td>
                  <td className="bl-td--r num bl-td--date">{dateShort(m.lastActive)}</td>
                  <td className="bl-td--act">
                    <span className="bl-rowact">
                      Open <Icon.Arrow size={13} />
                    </span>
                  </td>
                </tr>
              );
            })}

            {end < rows.length && spacer((rows.length - end) * ROW_H, 'bottom')}
          </tbody>
        </table>
      </div>

      {windowed && (
        <p className="bl-results__vnote meta">
          {int(rows.length)} rows · {int(end - start)} drawn. The list is windowed — scrolling
          renders the rest.
        </p>
      )}
    </div>
  );
}
