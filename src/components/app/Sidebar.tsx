import { NavLink, Link } from 'react-router-dom';
import { Logo } from '../primitives/Logo';
import { TokenMark } from '../primitives/TokenMark';
import { Icon } from './Icons';
import { watchlist, history } from '../../data/lists';
import { KOLS } from '../../data/kols';

const NAV = [
  { to: '/app/new', label: 'New Workspace', hint: 'Start an investigation', icon: Icon.New },
  { to: '/app/portfolio', label: 'Portfolio', hint: 'Paper agent · forward', icon: Icon.Portfolio },
  { to: '/app/trending', label: 'Trending Tokens', hint: 'Discovery', icon: Icon.Trend },
  { to: '/app/launches', label: 'Fresh Launches', hint: 'Scored at minute 5', icon: Icon.Launch },
  { to: '/app/wallets', label: 'Screener', hint: 'Cross-project wallets', icon: Icon.Screen },
  { to: '/app/kols', label: 'KOLs', hint: 'Accounts & records', icon: Icon.Kol },
  { to: '/app/watchlist', label: 'Watchlist', hint: 'Saved projects', icon: Icon.Watch },
  { to: '/app/history', label: 'Research History', hint: 'Past investigations', icon: Icon.History },
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
  const counts: Record<string, number | undefined> = {
    '/app/kols': KOLS.length,
    '/app/watchlist': watchlist.length,
    '/app/history': history.length,
  };

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

      {!collapsed && (
        <div className="bl-rail__recent">
          <p className="eyebrow bl-rail__recentl">Recent</p>
          {history.slice(0, 3).map((h) => (
            <Link
              key={h.id + h.time}
              to={`/app/project/${h.id}`}
              className="bl-recent"
              onClick={onNavigate}
            >
              <TokenMark logo={h.logo} monogram={h.monogram} size={20} radius={6} />
              <span className="bl-recent__n">{h.name}</span>
              <span
                className="bl-recent__r num"
                data-level={h.riskLevel}
                title={`Risk ${h.risk} / 100`}
              >
                {h.risk}
              </span>
            </Link>
          ))}
        </div>
      )}

      <div className="bl-rail__foot">
        <button className="bl-railitem bl-railitem--quiet" title="Settings">
          <span className="bl-railitem__i">
            <Icon.Settings />
          </span>
          {!collapsed && (
            <span className="bl-railitem__b">
              <span className="bl-railitem__l">Settings</span>
            </span>
          )}
        </button>
        <div className="bl-profile" data-collapsed={collapsed}>
          <span className="bl-profile__av">RA</span>
          {!collapsed && (
            <span className="bl-profile__b">
              <span className="bl-profile__n">Research account</span>
              <span className="bl-profile__p meta">Prototype · local</span>
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}
