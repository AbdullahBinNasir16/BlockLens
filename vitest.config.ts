import { defineConfig } from 'vitest/config';

/* Unit tests run in Node against the pure libraries: the screener evaluator,
   the formatters, the project registry and the live-feed helpers. Nothing
   here needs a DOM, and nothing may touch the network. */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/lib/**', 'src/data/projects/index.ts'],
      reporter: ['text', 'lcov'],
    },
  },
});
