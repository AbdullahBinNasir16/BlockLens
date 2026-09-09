import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlist } from '../data/lists';
import { TokenMark, ChainDot } from '../components/primitives/TokenMark';
import { Sparkline } from '../components/primitives/Charts';
import { MiniRing } from '../components/primitives/Meters';
import { Icon } from '../components/app/Icons';
import { compact, price, pct, bandColor } from '../lib/format';

export function WatchlistPage() {
  const nav = useNavigate();
  const [removed, setRemoved] = useState<string[]>([]);
  const rows = watchlist.filter((w) => !removed.includes(w.id));

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Saved</p>
          <h1 className="display d2">Watchlist</h1>
          <p className="bl-page__sub">
            Projects you are tracking. Risk is re-scored on every investigation.
          </p>
        </div>
        <div className="bl-page__headr">
          <span className="meta">{rows.length} projects</span>
        </div>
      </header>

      {rows.length === 0 ? (
        <div className="bl-empty">
          <svg viewBox="0 0 48 48" width="34" height="34" aria-hidden="true">
            <circle
              cx="24"
              cy="24"
              r="22"
              fill="none"
              stroke="var(--rule-strong)"
              strokeWidth="1"
              strokeDasharray="3 4"
            />
          </svg>
          <div>
            <p className="bl-empty__t">Watchlist is empty</p>
            <p className="bl-empty__d meta">Star a project from any investigation to track it.</p>
          </div>
        </div>
      ) : (
        <div className="bl-tablewrap">
          <table className="bl-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Chain</th>
                <th className="bl-th--c">Risk</th>
                <th className="bl-th--r">Change</th>
                <th className="bl-th--r">Price</th>
                <th className="bl-th--r">24h</th>
                <th className="bl-th--c">Trend</th>
                <th className="bl-th--r">Liquidity</th>
                <th className="bl-th--r">Last researched</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => (
                <tr key={w.id} className="bl-tr" onClick={() => nav(`/app/project/${w.id}`)}>
                  <td>
                    <span className="bl-tokencell">
                      <TokenMark
                        logo={w.logo}
                        monogram={w.monogram}
                        chain={w.chain}
                        size={34}
                        chainBadge
                      />
                      <span className="bl-tokencell__b">
                        <span className="bl-tokencell__n">{w.name}</span>
                        <span className="bl-tokencell__t meta">${w.ticker}</span>
                      </span>
                    </span>
                  </td>
                  <td>
                    <ChainDot chain={w.chain} />
                  </td>
                  <td className="bl-td--c">
                    <span className="bl-riskcell">
                      <MiniRing value={w.risk} color={bandColor[w.riskLevel]} size={38} stroke={3}>
                        <span style={{ fontSize: 11 }}>{w.risk}</span>
                      </MiniRing>
                      <span className="bl-riskcell__l meta" style={{ color: bandColor[w.riskLevel] }}>
                        {w.riskLevel}
                      </span>
                    </span>
                  </td>
                  <td
                    className="bl-td--r num"
                    style={{
                      color:
                        w.riskDelta === 0
                          ? 'var(--ink-4)'
                          : w.riskDelta < 0
                            ? 'var(--pos)'
                            : 'var(--neg)',
                    }}
                  >
                    {w.riskDelta === 0 ? '—' : `${w.riskDelta > 0 ? '+' : ''}${w.riskDelta}`}
                  </td>
                  <td className="bl-td--r num">{price(w.price)}</td>
                  <td
                    className="bl-td--r num"
                    style={{ color: w.change24h >= 0 ? 'var(--pos)' : 'var(--neg)' }}
                  >
                    {pct(w.change24h)}
                  </td>
                  <td className="bl-td--c">
                    <Sparkline
                      values={w.spark}
                      width={72}
                      height={22}
                      color={w.change24h >= 0 ? 'var(--pos)' : 'var(--neg)'}
                    />
                  </td>
                  <td className="bl-td--r num">${compact(w.liquidity)}</td>
                  <td className="bl-td--r meta">{w.lastResearched}</td>
                  <td className="bl-td--act">
                    <span className="bl-rowacts">
                      <button
                        className="bl-iconbtn"
                        title="Remove from watchlist"
                        onClick={(e) => {
                          e.stopPropagation();
                          setRemoved((r) => [...r, w.id]);
                        }}
                      >
                        <Icon.Star size={14} filled />
                      </button>
                      <span className="bl-rowact">
                        Open <Icon.Arrow size={13} />
                      </span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
