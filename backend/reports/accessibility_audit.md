# Accessibility audit (automated), 2026-11-21

**Promise:** slide 10, "works without perfect sight or a mouse".
**Scope of this audit:** automated only. It does not replace a manual
audit (see the last section).

## Method

- `e2e/a11y.spec.ts` (Playwright + axe-core 4.14.0) loads all 11 screens:
  landing, new investigation, case study, live token, trending, fresh
  launches, wallet screener, model health, portfolio, watchlist and history.
- On each screen it runs axe with the WCAG 2.1 A and AA rule sets.
- It also checks that all 8 workspace navigation links can be reached
  with the Tab key alone.
- It runs in CI with every Playwright run and fails on any serious or
  critical violation, so a regression is caught.

## First run, before fixes

| Rule | Impact | Elements | Screens | Cause |
|---|---|---:|---:|---|
| colour-contrast | serious | 124 | 10 | Text in `--ink-4` (#9a9891) at 2.7:1 on paper; amber `--warn` text at 3.4–3.7:1; green "Live" chip at 4.25:1. AA needs 4.5:1 |
| scrollable-region-focusable | serious | 2, then 1 | 2 | The workspace's main pane and wide tables scroll but could not take keyboard focus |
| aria-prohibited-attr | serious | 1 | 1 | The "derived" ring in the screener legend had `aria-label` on a plain `span` |

Keyboard: all 8 navigation links were reachable by Tab (8 of 8).

## Fixes

- **Colour tokens** (`src/styles/global.css`): ink-4 #9a9891 → #6d6c67;
  ink-3 #6b6a64 → #55544f, so the step between them is kept; `--warn`
  #a8790e → #8b640c; `--pos` #1a7f4b → #197948. Each new value is the
  smallest darkening of the old one that reaches 4.5:1 on every surface
  it is drawn on. The 0.9 opacity on provenance chip notes was removed.
- **Focus:** the main pane and the 8 scrollable table wrappers take
  `tabIndex={0}`, so they can be scrolled from the keyboard. A
  `:focus-visible` outline was already global.
- **ARIA:** the legend ring now has `role="img"`.

## Second run, after fixes

0 violations on all 11 screens. axe left 0 to 2 "needs review" items per
screen, which a person has to check. Keyboard: 8 of 8.

## What this does not show

Automated checks find only part of the real problems. Not done:
- a screen-reader pass (NVDA or VoiceOver) through the main tasks;
- whether charts are understandable without colour. The report figures
  were checked in greyscale (`report/figures/generated/greyscale_proof/`);
  the app's charts were not;
- whether focus order makes sense on every screen;
- 200% zoom and reflow at 320 px;
- any test with users who rely on assistive technology.

> **[Ours to write]** Whether this meets the slide-10 promise, and what
> the manual audit in FYP 2 must cover.
