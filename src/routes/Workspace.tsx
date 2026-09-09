import { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/app/Sidebar';
import { Icon } from '../components/app/Icons';
import { Logo } from '../components/primitives/Logo';
import { useMediaQuery } from '../lib/hooks';

export function Workspace() {
  const isNarrow = useMediaQuery('(max-width: 900px)');
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    setDrawer(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = drawer ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [drawer]);

  return (
    <div className="bl-ws" data-collapsed={collapsed}>
      {!isNarrow && (
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      )}

      {isNarrow && (
        <>
          <header className="bl-ws__bar">
            <button
              className="bl-ws__menu"
              onClick={() => setDrawer(true)}
              aria-label="Open navigation"
            >
              <Icon.Menu />
            </button>
            <Logo size={19} />
            <span />
          </header>
          {drawer && (
            <div className="bl-ws__drawer">
              <button
                className="bl-ws__scrim"
                onClick={() => setDrawer(false)}
                aria-label="Close navigation"
              />
              <div className="bl-ws__drawerpanel">
                <Sidebar
                  collapsed={false}
                  onToggle={() => setDrawer(false)}
                  onNavigate={() => setDrawer(false)}
                />
              </div>
            </div>
          )}
        </>
      )}

      <main className="bl-ws__main">
        <Outlet />
      </main>
    </div>
  );
}
