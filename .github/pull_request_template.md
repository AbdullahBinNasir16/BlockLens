## What

<!-- One paragraph: what changes and why. Link the issue if there is one. -->

## How to check it

<!-- Steps a reviewer can follow, or the test that proves it. -->

## Checklist

- [ ] Branched from `develop` (or `main` for a hotfix) and targets it
- [ ] `npm run typecheck && npm test && npm run build` pass locally
- [ ] `cd backend && python -m pytest -q` passes locally (if the backend changed)
- [ ] Any new number shown in the UI says where it comes from (Sourced / Sample / live API)
- [ ] `DECISIONS.md` updated if a design decision was made
