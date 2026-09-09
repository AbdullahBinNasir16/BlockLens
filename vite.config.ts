import { defineConfig, type ProxyOptions } from 'vite';
import react from '@vitejs/plugin-react';

/* The live trending page calls GeckoTerminal, DexScreener and GoPlus through
   these same-origin paths. GeckoTerminal sends its 429s without CORS
   headers, so called directly a rate limit reads as a network failure;
   through the proxy the page sees the real status and backs off. */
const proxy: Record<string, ProxyOptions> = {
  /* The BlockLens API (backend/blocklens/api), for the live launch feed. */
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
  '/gt': {
    target: 'https://api.geckoterminal.com/api/v2',
    changeOrigin: true,
    rewrite: (p) => p.replace(/^\/gt/, ''),
  },
  '/ds': {
    target: 'https://api.dexscreener.com',
    changeOrigin: true,
    rewrite: (p) => p.replace(/^\/ds/, ''),
  },
  '/gp': {
    target: 'https://api.gopluslabs.io',
    changeOrigin: true,
    rewrite: (p) => p.replace(/^\/gp/, ''),
  },
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
