# BlockLens backend — Phases 1 to 5

Ingestion, storage, and the labelled dataset, for one chain. Base, on free
keyless sources: a public RPC gateway for the chain, DexScreener for market
state. No API key is required to run anything here, and nothing in either
phase spends money.

* **Phase 1** collects each token's first 24 hours — the features.
* **Phase 2** decides what happened to it 90 days later — the labels, and a
  defence of them.
* **Phase 3** builds the wallet graph — funding edges, clusters, and 95
  propagated features per wallet.
* **Phase 4** trains the risk model, and reports that its headline result is
  **negative**: graph structure alone does not beat a permutation null on
  this dataset. See [`reports/model_card.md`](reports/model_card.md).

The chain choice, the cost measurements behind it, and every deviation from
the original brief are argued in [`../DECISIONS.md`](../DECISIONS.md). The
empirical work that preceded this code is in
[`spikes/FINDINGS.md`](spikes/FINDINGS.md).

## What it does

1. **Discovers** new pools by reading pool-creation events straight from the
   chain — Uniswap V4 `Initialize` and V3 `PoolCreated`. Not from
   DexScreener's new-token feeds, which carry no Base tokens at all.
2. **Backfills** each token's first 24 hours of transfers and swaps, in
   1,000-block windows, resuming from a checkpoint if it stops.
3. **Enriches** tokens with symbol, name, liquidity and dollar price from
   DexScreener, and records a `pair_snapshot` on every poll.

## Running it

```bash
python -m pip install -e .
docker compose up -d                 # PostgreSQL 16 + TimescaleDB
python -m alembic upgrade head

python -m scripts.ingest discover --limit 100        # new pools, last 6h
python -m scripts.ingest backfill --all-pending      # first 24h of each
python -m scripts.ingest status                      # rows, runs, spend
python -m scripts.ingest first-hour --token 0x…      # the cohort query
```

`discover` should run often. A launch's transfers can be recovered from logs
at any time, but its *market state* at the moment it launched cannot — every
hour the poller is not running is an hour of `pair_snapshot` history that no
later run can reconstruct. So leave it polling:

```bash
python -m scripts.ingest discover --watch 900     # every 15 minutes
```

Each pass is its own `ingest_run`, so a crash mid-poll shows up in the run
table rather than vanishing inside a long-lived process, and a failing pass
is reported without ending the loop.

A note on bounding a run: `--max-calls` is the limit that bites. `--max-cu`
counts Alchemy compute units, and the keyless sources this project runs on
charge none — so it is inert without a key, and the CLI says so rather than
accepting a ceiling that bounds nothing.

To backfill tokens whose 24 hours have already closed, point discovery at an
older window:

```bash
python -m scripts.ingest discover --offset-hours 26 --hours 1.5
```

### Without Docker

The development machine this was built on cannot run Docker, so the store
also runs on a portable PostgreSQL 16 with no admin rights and no
TimescaleDB. The hypertable migration is guarded and skipped there; a plain
table answers every Phase 1 query correctly, just more slowly.

```bash
export DATABASE_URL=postgresql+psycopg://blocklens@127.0.0.1:5433/blocklens
```


## Phase 2: the labelled set

```bash
python -m scripts.label build                    # label everything eligible
python -m scripts.label status                   # class counts and base rate
python -m scripts.label sample --label RUG -n 10 # random rows, with evidence
python -m scripts.label show --token 0x...       # one verdict in full
python -m scripts.label_sensitivity              # sweep every threshold
python -m scripts.dataset_card                   # the data card
```

The chain never records "this was a rug pull" — it records liquidity moving,
and an honest migration looks identical to a theft. So the label does not
exist until it is defined, and the definition is the contribution rather than
a detail. It lives in [`blocklens/label/rules.py`](blocklens/label/rules.py):
every criterion is a separate named boolean, every threshold is a constant,
and the combination is one readable expression.

Four classes, and the distinctions are deliberate:

| Class | Means |
|---|---|
| `RUG` | token reserve collapsed inside one sampling window |
| `FAILED` | price collapsed or trading stopped, *without* a reserve collapse |
| `SURVIVED` | still holds its liquidity and still trades |
| `UNCLEAR` | none of the above, or too few observations to judge |
| `NEVER_LAUNCHED` | never traded — excluded from the set, not a finding |

`RUG` and `FAILED` stay apart: a token nobody wanted is not a token whose
deployer took the money, and merging them teaches a model "this went down",
which is not worth predicting. The binary target is `RUG` against the rest,
collapsed at training time.

### How the evidence is gathered

Reserves and prices are **sampled** at historical blocks rather than
reconstructed from transfers. The brief specified reconstruction; it was
measured and rejected, because the keyless gateway caps `eth_getLogs` at
1,000 blocks however narrowly the query is filtered — 3,888 calls per token
for 90 days. Archive `eth_call` works on the same endpoint at least 365 days
back, so a reserve can be read at a block instead of accumulated: 90 daily
points in 43 seconds. It is also more accurate, because a cumulative sum is
wrong forever if one window is missed, whereas each sample is independent.

Uniswap V4 needed its own answer, and it is most of Base. One PoolManager
holds every pool's quote token, so a per-pool quote reserve cannot be read —
but it holds *one token* only on account of pools containing that token, so
for a launch with a single pool, `balanceOf(token, PoolManager)` is that
pool's reserve exactly. Checked against Phase 1's own stored transfers for
five tokens: exact to the wei on all five. Price comes from `extsload` on
the PoolManager, cross-checked against the official StateView.

Full measurements in [`spikes/B_FINDINGS.md`](spikes/B_FINDINGS.md).

### What a label does not claim

* **Who pulled the liquidity.** `largest_outflow_to` records where the
  biggest outflow went, as evidence. Attributing it to the deployer needs a
  funding cluster, which is Phase 3, so no row asserts attribution.
* **A dollar price.** Prices are ratios against each token's own quote
  asset, used only to compare a token against its own peak.
* **Intent.** The chain records movement, not motive.

### Re-arguing a threshold costs nothing

Every row stores the observations it was built from (`series_json`), so
`label_sensitivity` re-derives every verdict offline at any threshold — the
observation window included. `rule_version` is part of the primary key, so a
changed threshold writes a new generation and the old verdicts stay for
comparison.

## Layout

```
blocklens/
  config.py            every tunable, from the environment
  store/
    models.py          the schema
    db.py              engine and sessions; writes nothing
    write.py           THE WRITE GATE — the only module that writes rows
  label/
    sample.py          reserve and price at historical blocks
    rules.py           THE DEFINITION — criteria, thresholds, combination
    build.py           orchestration; refuses anything too young
  ingest/
    budget.py          token buckets, monthly ledger, hard ceilings
    sources.py         all HTTP; explicit timeouts and retries
    evm.py             keccak, event topics, log decoding
    chain.py           discovery and backfill
    dexscreener.py     enrichment and snapshots
    xapi.py            built, tested, and switched off
    runner.py          run lifecycle and bookkeeping
scripts/ingest.py      the ingestion CLI
scripts/label.py       the labelling CLI
scripts/label_sensitivity.py
scripts/dataset_card.py
reports/               generated: sensitivity, dataset card
migrations/            alembic
tests/                 46 tests, no network
```

## The two invariants

**Every row enters through `store/write.py`.** Nothing else writes. Each
entry point takes an explicit `as_of_ts`, and the gate raises
`LookaheadError` if any row in the batch carries a timestamp later than it —
the whole batch, not just the offending row, because a partial write would
leave the caller believing it had a complete window. This looks like overkill
while nothing computes features. It is the mechanism that makes lookahead
impossible later, and it has to exist before anything depends on it.

**Every metered call goes through `ingest/budget.py`.** A token bucket per
source keeps the project a polite guest on infrastructure it does not own, a
monthly counter persisted in the database survives restarts, and a hard
ceiling stops a run cleanly rather than burning an allowance overnight.

## What the data does not claim

* `swap.wallet_address` is **NULL**. The spike proved the transfer
  counterparty on an aggregator route is the router, not the trader, and
  recording a router as a wallet would poison every wallet-level metric the
  project exists to compute. Direction and amounts are still correct — they
  are read from the token's own transfers rather than from the event's sign.
* `swap.price_usd` is set only for stablecoin-quoted pools. A WETH-quoted
  price needs a historical ETH series, which Phase 1 does not have.
  `quote_amount` is always recorded, so the price can be derived later.
* `wallet.funding_source` is **`unknown`** everywhere. Labelling it costs
  more than the transfers do; that is Phase 3.
* `provenance` is `live` on every row written by this code. Nothing here
  generates sample data.

## Tests

```bash
python -m pytest -q
```

No test touches the network — the transport is blocked for the whole suite,
so a test that leaks a real call fails rather than quietly passing against a
live API. The API fixtures in `tests/fixtures/` are genuine recorded
responses, re-recordable with `python -m tests.record_fixtures`. The one
exception is `x_search_recent.json`, which is synthetic and says so in the
file: recording it needs a paid bearer token.

The store tests run against a real PostgreSQL rather than SQLite, because the
idempotency proof depends on `ON CONFLICT DO UPDATE` and on the `xmax = 0`
trick that distinguishes an insert from an update. Proving it on another
engine would prove nothing about the one that ships.

## X / Twitter

`ingest/xapi.py` is the only source that can cost real money, so it is the
one source that cannot run by accident. It is built, it is tested against a
recorded fixture, and it has three independent locks: `X_ENABLED` is unset,
`X_POST_BUDGET` is **0** posts, and no CLI command reaches it. Per the brief,
it was not run in Phase 1 at all.


## Phase 5: integrity audit, a powered dataset, and the retrain

```bash
python -m scripts.leakage_audit                      # Part A -> reports/leakage_audit.md
python -m scripts.phase5 verify-batch                # batched reads == stored reads
python -m scripts.phase5 discover --stratum random   # uniform windows, outcome-blind
python -m scripts.phase5 discover --stratum train --rounds 10
python -m scripts.phase5 coarse --worker 0/2         # case-control pre-screen
python -m scripts.phase5 select-train
python -m scripts.phase5 backfill && python -m scripts.phase5 alive
python -m scripts.phase5 families
python -m scripts.phase5 label --stratum random --worker 0/3
python -m scripts.phase5 status
python -m scripts.phase5_model features && python -m scripts.phase5_model run
python -m scripts.phase5_counts
```

Read [`reports/model_card_v2.md`](reports/model_card_v2.md) before quoting
any number. The short version: at launch + 5 minutes, liquidity-pull rugs on
Base are almost decided by launch type (self-deployed vs launchpad), a
one-line liquidity-lock rule scores PR-AUC 0.965, the model 0.999, and the
graph features add nothing at token or wallet level.

## Phase 7: the API and the live launch feed

```bash
python -m scripts.train_buyer_loss                       # data/models/buyer_loss_v1.joblib
uvicorn blocklens.api.app:app --port 8000                # API + live scorer loop
```

Then `npm run dev` in the repo root: the front end's **Fresh Launches**
page (`/app/launches`) reads `/api/launches` through the Vite proxy.

Every minute the scorer finds new Base Uniswap pools, waits until each is
five minutes old, backfills those five minutes, computes the same features
the model was trained on, and attaches two signals:

* **Launch type:** self-deployed (liquidity withdrawable) or launchpad
  (locked).
* **Buyer-loss risk** from `buyer_loss_v1`.

A pool outside the training conditions gets a reason, not a number. Every
API response carries the model's validation record.

| endpoint | returns |
|---|---|
| `GET /api/launches` | last 6 hours of tracked launches, with the model's validation record |
| `GET /api/token/{address}` | that launch's signals, if tracked |
| `GET /api/model` | model metadata |
| `GET /api/health` | last scan, last error |

Set `BLOCKLENS_LIVE=0` to serve without the background loop (the tests do).

## Phase 8: forward validation (running)

```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\start_live.ps1   # postgres + API, detached
powershell -ExecutionPolicy Bypass -File backend\scripts\stop_live.ps1
```

* **Logging:** while the API runs, every launch the feed reaches a verdict
  on is written once to `live_prediction`.
* **Buyer loss:** resolved at hour 6 by the same code as the label.
* **Liquidity pulled:** read at days 1, 7, 30 and 90 from pool reserves.
* **Scoreboard:** `GET /api/forward`, and the panel on Fresh Launches. Both
  say "too early" until the pre-registered floor of 200 resolved
  predictions with 20 losses is reached.

The protocol, the frozen model and the success criterion are in
DECISIONS.md, Phase 8, and were written before the first outcome.

The stack does not survive a reboot or logoff on its own. Run
`start_live.ps1` again, or register it to run at logon.

The stack starts automatically at logon through a per-user Windows
scheduled task, **"BlockLens live stack"** (registered 2026-10-21). Remove
it with:

```powershell
Unregister-ScheduledTask -TaskName 'BlockLens live stack' -Confirm:$false
```

## Phase 10: the product around the signal

| endpoint | returns |
|---|---|
| `GET /api/explain` | how explanations are built: base rate, feature labels |
| `GET /api/token/{address}` | now carries `launch.why`: the score's top movers, each with its value and its log-odds contribution |
| `GET /api/paper-agent/trades` | the paper agent's book, trade by trade, newest first |
| `GET /api/model/health` | launches a day and why each was or was not scored, launch-type drift, scoring delay, outages |
| `GET /api/stream` | server-sent events: `hello`, then `scored` per newly scored launch (`?ticks=1` for a one-shot check) |
| `GET/POST /api/watchlist`, `DELETE /api/watchlist/{address}` | the watchlist |
| `GET/POST /api/history` | investigations opened, newest first |

Alerts: set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` and every scored
launchpad launch with risk under `ALERT_MAX_RISK` (default 0.2, the paper
agent's ceiling) is sent to that chat. Unset, nothing is sent; `/api/health`
reports the channel's state either way.

Migration `b7a8c9d0e1f2` adds the two product tables and the `explanation`
column; run `python -m alembic upgrade head` on an existing store.
