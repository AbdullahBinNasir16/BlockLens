# Reproducing BlockLens's numbers

This reproduces every figure and headline number in the FYP-1 report on a
clean machine. There are two tiers, because rebuilding the dataset from the
chain itself takes days of rate-limited calls:

| Tier | Starts from | Gets you | Time | Verified |
|---|---|---|---|---|
| **A** | the repository + a snapshot of the store | every figure, `results/manifest.json`, the model | ~10 min after setup | **yes**, on a fresh checkout (see the record at the end) |
| **B** | the repository + an empty database | the store itself: discovery, labels, features | days (≈ 300k RPC calls) | step by step during development; **not re-run end to end** |

Every number the report quotes comes from `results/manifest.json`, which
Tier A regenerates. Seeds are fixed in one place, `blocklens.config.Seeds`.
Splits and windows are constants in `blocklens/sampling/design.py`.

---

## Setup (both tiers)

You need Git, Python 3.12 or later (results were produced on 3.14.2),
PostgreSQL 16, and Node 20 for the front end.

```sh
git clone https://github.com/AbdullahBinNasir16/BlockLens.git
cd BlockLens/backend
python -m venv .venv
.venv/Scripts/activate            # Windows; on Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.lock      # the exact versions that produced the results
python -m pip install --no-deps -e .
```

`requirements.lock` is a full `pip freeze` of the environment that
produced `results/manifest.json`. `pyproject.toml` pins the direct
dependencies.

Point the backend at your database with `DATABASE_URL`, for example
`postgresql+psycopg://blocklens@127.0.0.1:5433/blocklens`. Every other
setting has a default (`.env.example`).

**Expected:** about 70 packages install; `python -c "import blocklens"`
succeeds.

---

## Tier A: from the store snapshot (minutes)

### A1. Restore the store

The store is about 5 GB (3.8 GB of it raw token transfers), too large for
git. Make a snapshot from a machine that has it:

```sh
pg_dump -Fc -Z 6 -f blocklens.dump "$DATABASE_URL_PLAIN"     # postgresql://user@host:port/db
```

and restore it on the new machine:

```sh
createdb blocklens
pg_restore -d blocklens --no-owner blocklens.dump
python -m alembic upgrade head        # no-op on a current snapshot
```

**Expected:** `token_label` holds 1,058 rows at rule `v2-2026-10`. The
manifest records a SHA-256 of `(token, label)` for the whole table
(`dataset.labels_sha256`), so a snapshot can be checked against the
numbers it should produce.

### A2. The caches

`backend/data/phase5_features.json` (minute-5 features) and
`backend/data/phase6_extraction.json` (the extraction label) are committed.
Nothing to do. To rebuild them from the store, see B4 and B5.

### A3. Regenerate every figure and the manifest

```sh
cd backend
python -m scripts.make_figures
```

**Expected:**
- **Time:** about 2.5 minutes. Most of it is permutation importance (30
  repeats) and bootstraps (1,000 resamples).
- **Output:** 11 figures in `report/figures/generated/` (PDF, SVG, and a
  greyscale proof of each), `captions.md` and `captions.tex`, and
  `results/manifest.json`.
- **Research numbers that must match exactly:** buyer-loss PR-AUC on the
  research cohort 0.8331 (boosting), 0.6435 (logistic), 0.3704 and 0.3651
  (checkers); out of time 0.7962; graph comparison 0.8279 / 0.5431 /
  0.8331. These depend only on the store and the seeds.
- **Forward numbers will differ:** the live record grows every minute.
  The manifest records the time they were read.

### A4. Retrain the shipped model (optional)

```sh
python -m scripts.train_buyer_loss
```

**Expected:** `data/models/buyer_loss_v1.joblib` and `.json`, fitted on
593 tokens with 176 losses.

### A5. Run the tests

```sh
python -m pytest -q          # needs a PostgreSQL test database, default <db>_test
cd .. && npm ci && npm test && npx tsc --noEmit -p .
```

**Expected:** backend 189 passed; frontend 40 passed.

---

## Tier B: from the chain (days)

These are the steps that built the store. Each runs against free keyless
endpoints, rate-limited by `ingest/budget.py`. The costs below are the
ones measured during development (`DECISIONS.md`).

| Step | Command | What it does | Measured cost |
|---|---|---|---|
| B1 | `python -m alembic upgrade head` | Empty schema | seconds |
| B2 | `python -m scripts.phase5 discover` | Draw the weekly windows (seeded) and find new Uniswap V3/V4 pools | ~15k pools screened |
| B3 | `python -m scripts.phase5 survivors`, `coarse`, `select-train`, `backfill`, `alive`, `families` | Screen, sample the strata, backfill the first 24 h of transfers and swaps, apply the minute-5 survival rule, build operator families | the bulk of ~297k RPC calls |
| B4 | `python -m scripts.phase5 label` and `python -m scripts.phase5_model features` | Rule v2 labels from archive reads over 90 days; minute-5 features → `data/phase5_features.json` | included above |
| B5 | `python -m scripts.phase6 extend` and `run` | 6-hour backfill and the extraction label → `data/phase6_extraction.json` | Phase 6 runs |
| B6 | `python -m scripts.phase5_model run`, `python -m scripts.phase6_model` | Phase 5 and 6 results JSON | minutes |
| B7 | Tier A, step A3 | Figures and manifest | minutes |

Running B2–B5 again reproduces the **design**, not the identical rows:
- **Windows** are drawn from a fixed seed, so the same windows are chosen.
- **Free endpoints** occasionally fail and are retried, and a
  later run sees the chain as it is now.

That is why Tier A, from a snapshot, is the reproduction of the reported
numbers.

**The live forward record** (Phase 8 onward) cannot be reproduced: it
records predictions made before their outcomes existed, which is its
point. It can be audited instead. `live_prediction` is append-only, every
row holds its score time, and the exclusion rules are in
`resolver.VALID_SQL`.

---

## Verification record

A fresh checkout of branch `feat/evidence-pack` was cloned into an empty
directory, with a new virtual environment installed from
`requirements.lock` alone. Its figures were regenerated against the store
and compared with the committed manifest. The result is recorded below by
the run that performed it.

**2026-11-21, Tier A, on a fresh checkout:**
- **Clone:** `62f565a` (branch `feat/evidence-pack`), cloned into an empty
  directory.
- **Environment:** a new virtual environment from `requirements.lock`
  (Python 3.14.2, Windows 11). The install took several minutes.
- **Run:** `python -m scripts.make_figures`, 2 min 8 s; 11 figures and the
  manifest written.
- **Compared** with the committed `results/manifest.json`. **Every
  research number matched exactly:**
  - buyer-loss PR-AUCs and intervals;
  - the graph comparison;
  - permutation importance (top 20);
  - label sensitivity;
  - class balance and base rates;
  - co-movement;
  - the cluster case;
  - out of time (0.7962) and the by-month table;
  - Brier scores;
  - the dataset hash.
- **Limit:** the fresh checkout read the **same PostgreSQL store**, not a
  dump restored onto another machine. This verifies the code, the
  environment and the committed caches, but not the `pg_dump` /
  `pg_restore` step in A1.
- **Tier B** was not re-run end to end.
