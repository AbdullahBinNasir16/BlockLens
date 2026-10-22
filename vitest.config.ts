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
      /* A floor CI enforces, ratcheted up as tests are added: the pure
         libraries are the testable surface; readers of public APIs are
         exercised end to end instead. */
      thresholds: { lines: 30, functions: 35, branches: 80 },
    },
  },
});
