import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';

import './styles/global.css';
import './styles/primitives.css';
import './styles/landing.css';
import './styles/app.css';
import './styles/research.css';
import './styles/screener.css';
import './styles/trending.css';
import './styles/live.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
