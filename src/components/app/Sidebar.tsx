import { NavLink, Link } from 'react-router-dom';
import { Logo } from '../primitives/Logo';
import { Icon } from './Icons';
import { shortAddr } from '../../lib/format';
import { findByContract } from '../../data/projects';
import { useProductState } from '../../lib/live/useProduct';

const NAV = [
  { to: '/app/new', label: 'New Investigation', hint: 'Any Base contract', icon: Icon.New },
  { to: '/app/launches', label: 'Fresh Launches', hint: 'Scored at minute 5', icon: Icon.Launch },
  { to: '/app/trending', label: 'Trending Tokens', hint: 'Discovery', icon: Icon.Trend },
  { to: '/app/portfolio', label: 'Paper Agent', hint: 'Forward record', icon: Icon.Portfolio },
  { to: '/app/model', label: 'Model Health', hint: 'Drift, outages, calibration', icon: Icon.Pulse },
  { to: '/app/wallets', label: 'Screener', hint: 'Cross-project wallets', icon: Icon.Screen },
  { to: '/app/watchlist', label: 'Watchlist', hint: 'Saved tokens', icon: Icon.Watch },
  { to: '/app/history', label: 'History', hint: 'Past investigations', icon: Icon.History },
];

export function Sidebar({
  collapsed,
  onToggle,
  onNavigate,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}) {
  const { watchlist, history, available } = useProductState();
  const counts: Record<string, number | undefined> = available
    ? { '/app/watchlist': watchlist.length, '/app/history': history.length }
    : {};
  const recent = history.slice(0, 3);

  return (
    <aside className="bl-rail" data-collapsed={collapsed}>
      <div className="bl-rail__top">
        <Link to="/" className="bl-rail__logo" onClick={onNavigate} title="BlockLens — home">
          <Logo size={20} wordmark={!collapsed} />
        </Link>
        <button
          className="bl-rail__toggle"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? <Icon.Expand /> : <Icon.Collapse />}
        </button>
      </div>

      <nav className="bl-rail__nav">
        {NAV.map((n) => {
          const I = n.icon;
          return (
            <NavLink
              key={n.to}
              to={n.to}
              className="bl-railitem"
              onClick={onNavigate}
              title={collapsed ? n.label : undefined}
            >
              <span className="bl-railitem__i">
                <I />
              </span>
              {!collapsed && (
                <span className="bl-railitem__b">
                  <span className="bl-railitem__l">{n.label}</span>
                  <span className="bl-railitem__h">{n.hint}</span>
                </span>
              )}
              {!collapsed && counts[n.to] !== undefined && (
                <span className="bl-railitem__c num">{counts[n.to]}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {!collapsed && recent.length > 0 && (
        <div className="bl-rail__recent">
          <p className="eyebrow bl-rail__recentl">Recent</p>
          {recent.map((h) => {
            const known = findByContract(h.address);
            const to = known ? `/app/project/${known.project.id}` : `/app/token/${h.address}`;
            return (
              <Link key={h.id} to={to} className="bl-recent" onClick={onNavigate}>
                <span className="bl-recent__n num">{known ? known.project.name : shortAddr(h.address, 6, 4)}</span>
                <span className="bl-recent__r meta" data-level={h.outcome}>
                  {h.outcome}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      <div className="bl-rail__foot">
        <div className="bl-profile" data-collapsed={collapsed}>
          <span className="bl-profile__av">BL</span>
          {!collapsed && (
            <span className="bl-profile__b">
              <span className="bl-profile__n">Single-user workspace</span>
              <span className="bl-profile__p meta">{available ? 'API connected' : 'API offline'}</span>
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}
