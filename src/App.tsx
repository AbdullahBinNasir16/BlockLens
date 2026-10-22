import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { Landing } from './routes/Landing';
import { Workspace } from './routes/Workspace';
import { NewInvestigation } from './routes/NewInvestigation';
import { Investigating } from './routes/Investigating';
import { ProjectIntelligence } from './routes/ProjectIntelligence';
import { Trending } from './routes/Trending';
import { Screener } from './routes/Screener';
import { Portfolio } from './routes/Portfolio';
import { WatchlistPage } from './routes/WatchlistPage';
import { HistoryPage } from './routes/HistoryPage';
import { UnresearchedToken } from './routes/UnresearchedToken';
import { Launches } from './routes/Launches';
import { ModelHealth } from './routes/ModelHealth';

function ScrollReset() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
    document.querySelector('.bl-ws__main')?.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export function App() {
  return (
    <>
      <ScrollReset />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Workspace />}>
          <Route index element={<Navigate to="/app/new" replace />} />
          <Route path="new" element={<NewInvestigation />} />
          <Route path="investigating" element={<Investigating />} />
          <Route path="project/:id" element={<ProjectIntelligence />} />
          <Route path="token/:address" element={<UnresearchedToken />} />
          <Route path="trending" element={<Trending />} />
          <Route path="launches" element={<Launches />} />
          <Route path="wallets" element={<Screener />} />
          <Route path="model" element={<ModelHealth />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="watchlist" element={<WatchlistPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
