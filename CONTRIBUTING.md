# Contributing

BlockLens is developed as a product, with the branch discipline and the
automated gates that implies. This page is the whole process.

## Branches

| Branch | Holds | Who merges into it |
|---|---|---|
| `main` | what is released: every commit is deployable, and CD publishes images from it | a reviewed pull request from `develop` |
| `develop` | the integration branch: finished features, always green | a reviewed pull request from a feature branch |
| `feature/<topic>` | one piece of work, branched from `develop` | its author, by pull request |
| `fix/<topic>` | a bug fix, branched from `develop` (or `main` for a hotfix) | by pull request |

Never commit straight to `main` or `develop`. Both are protected: a pull
request needs the CI check green and one review before it can merge.

## The loop

```bash
git checkout develop && git pull
git checkout -b feature/short-topic
# work, in small commits
git push -u origin feature/short-topic
gh pr create --base develop --fill
```

CI runs on the pull request. Fix anything red, push again, request a review.
Merge with **squash** so `develop` reads one line per feature.

A release is a pull request from `develop` into `main`, then a tag:

```bash
git tag v0.2.0 && git push origin v0.2.0
```

The tag builds a GitHub Release with the web bundle attached, and the merge
publishes `blocklens-web` and `blocklens-api` images to GHCR.

## Commit messages

Conventional prefixes, as the history already uses them:
`feat`, `fix`, `test`, `ci`, `build`, `docs`, `chore`, `refactor`, `report`.
A scope in brackets where it helps: `feat(ui): …`, `fix(api): …`.
Subject in the imperative, under 72 characters; the body says why.

## What CI checks

* **Frontend:** `npm run typecheck`, `npm test` (vitest), `npm run build`.
* **Backend:** `pytest` against a real PostgreSQL service, with the network
  transport blocked for the whole suite.

Run the same locally before pushing:

```bash
npm run typecheck && npm test && npm run build
cd backend && python -m pytest -q
```

## Adding tests

* Frontend unit tests sit beside the module they test, as `*.test.ts`, and
  import only from `src/lib` and `src/data`. No DOM, no network.
* Backend tests go in `backend/tests/`. Record a fixture rather than
  calling an API; the transport block will fail a test that leaks a call.
