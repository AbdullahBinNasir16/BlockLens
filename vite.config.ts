import { defineConfig, type ProxyOptions } from 'vite';
import react from '@vitejs/plugin-react';

/* The dev server proxies only the BlockLens API. Since Phase 7 the browser
   never calls a third party: the API proxies GeckoTerminal, DexScreener and
   GoPlus itself (backend/blocklens/api/market.py), so a production build
   needs no proxy for them. Set VITE_API_URL to point a build elsewhere. */
const proxy: Record<string, ProxyOptions> = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, open: false, proxy },
  preview: { proxy },
  build: {
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
});
