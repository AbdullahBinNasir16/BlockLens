"""Live scoring of new Base launches at launch + 5 minutes.

The only place the research models meet live data. Two signals, and
nothing else, because they are the two Phase 5 and 6 could defend:

* **Launch type**, read at minute 0. A self-deployed token, whose deployer
  holds withdrawable liquidity, was liquidity-pulled 109 times in 113 in
  the held-out cohort; a launchpad token, minted and given locked liquidity
  in one transaction, 0 times in 74.
* **Buyer-loss risk**, scored once at minute 5 by `buyer_loss_v1`: will a
  buy at this price be worth half or less six hours after launch?

A pool gets a number only when the scoring conditions of the training data
hold. Otherwise it gets the reason it was not scored, and that reason is
shown to the user rather than a guess.

Features come from `token_features.token_row`, the same code the model was
trained with, after backfilling the pool's first five minutes into the
store. Live tokens are recorded in `token_sample` as stratum `live` with an
exclusion reason, so research queries never pick them up.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sqlalchemy import text

from ..ingest import chain as chain_ingest
from ..ingest import dexscreener as ds_ingest
from ..ingest.budget import Budget
from ..ingest.evm import UNISWAP_V4_POOL_MANAGER, V3_SWAP, V4_SWAP
from ..ingest.sources import PooledRpcSource
from ..model import token_features as tf
from ..sampling import design as d
from ..store.db import session_factory
from . import resolver

CHAIN = "base"
MODEL_PATH = Path("data/models/buyer_loss_v1.joblib")
STATE_PATH = Path("data/live_launches.json")
LOOKBACK_BLOCKS = 1800          # first start: the last hour
KEEP_HOURS = 6
POLL_SECONDS = 60
CONTEXT_REFRESH_SECONDS = 3600
STABLES = {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
           "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"}


@dataclass
class Launch:
    token: str
    pool: str
    dex: str
    quote: str
    created_block: int
    launch_ts: str
    status: str = "waiting for minute 5"
    launch_type: str | None = None          # "launchpad" | "self-deployed"
    risk: float | None = None               # buyer-loss probability
    swaps_by_cutoff: int | None = None
    buyers_by_cutoff: int | None = None
    run_up_by_cutoff: float | None = None
    scored_at: str | None = None
    notes: list[str] = field(default_factory=list)


class Scorer:
    def __init__(self) -> None:
        art = joblib.load(MODEL_PATH)
        self.model, self.meta = art["model"], art["meta"]
        self.launches: dict[str, Launch] = {}
        self.scanned_to: int | None = None
        self.last_run: str | None = None
        self.last_error: str | None = None
        self._ctx: tf.Context | None = None
        self._ctx_at = 0.0
        self._lock = threading.Lock()
        self._features: dict[str, dict] = {}
        self.forward: dict | None = None
        self._load()

    # ---- persistence -------------------------------------------------------

    def _load(self) -> None:
        try:
            doc = json.loads(STATE_PATH.read_text(encoding="utf8"))
            self.scanned_to = doc.get("scanned_to")
            for k, v in doc.get("launches", {}).items():
                self.launches[k] = Launch(**v)
        except (FileNotFoundError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        doc = {"scanned_to": self.scanned_to,
               "launches": {k: asdict(v) for k, v in self.launches.items()}}
        STATE_PATH.write_text(json.dumps(doc), encoding="utf8")

    # ---- the loop ---------------------------------------------------------

    def run_forever(self) -> None:
        while True:
            try:
                self.tick()
                self.last_error = None
            except Exception as e:  # noqa: BLE001 - the loop must survive a bad tick
                self.last_error = f"{type(e).__name__}: {str(e)[:200]}"
            time.sleep(POLL_SECONDS)

    def tick(self) -> None:
        rpc = PooledRpcSource(Budget(max_calls=20_000))
        clock = d.Clock(rpc)
        # A few blocks behind the head: endpoints disagree about the tip, and the
        # log endpoint refuses ranges past its own.
        head = clock.head - 5
        start = self.scanned_to + 1 if self.scanned_to else head - LOOKBACK_BLOCKS
        # discover in 1,000-block steps
        b = start
        while b <= head:
            w = d.Window(id="live", stratum="live", round=0, week=-1,
                         start_ts=clock.ts_of(b), start_block=b)
            hi = min(head, w.end_block)
            for c in d.discover(rpc, w, to_block=hi):
                if c["created_block"] > hi:
                    continue
                key = c["token_address"]
                if key in self.launches:
                    continue
                launch = Launch(token=key, pool=c["pool_key"], dex=c["dex"],
                                quote=(c.get("quote_address") or "").lower(),
                                created_block=c["created_block"],
                                launch_ts=clock.ts_of(c["created_block"]).isoformat())
                if d.degenerate_start(c):
                    launch.status = "not scored: pool initialised at an untradeable price"
                with self._lock:
                    self.launches[key] = launch
            b = hi + 1
        self.scanned_to = head

        with self._lock:
            pending = list(self.launches.values())
        # A launch already past its six-hour mark (an outage) is not scored: its
        # outcome exists, so a score could not count, and screening a backlog
        # would delay the launches that still can (DECISIONS.md, Phase 8 note).
        horizon = head - resolver.WINDOW_BLOCKS
        missed = [l for l in pending
                  if l.status == "waiting for minute 5" and l.created_block < horizon]
        for l in missed:
            l.status = "not scored: missed during an outage (past its 6-hour mark)"
        if missed:
            with session_factory()() as s:
                for l in missed:
                    resolver.record(s, launch=l, model_version=self.meta["version"],
                                    features=None, reserve_cutoff=None)
                s.commit()
        due = [l for l in pending
               if l.status == "waiting for minute 5" and head >= l.created_block + d.CUTOFF_BLOCKS + 5]
        if due:
            self._screen(rpc, due)
            with session_factory()() as s:
                ctx = self._context(s)
                for l in due:
                    if l.status == "waiting for minute 5":
                        self._score(s, rpc, ctx, l, clock)
                # Phase 8: every final status is logged once, scored or not
                for l in due:
                    if l.status == "waiting for minute 5":
                        continue
                    rc = None
                    if l.status == "scored":
                        rc = resolver.reserve_at(rpc, token=l.token, pool=l.pool, dex=l.dex,
                                                 block=l.created_block + d.CUTOFF_BLOCKS)
                    resolver.record(s, launch=l, model_version=self.meta["version"],
                                    features=self._features.pop(l.token, None), reserve_cutoff=rc)
                s.commit()
        with session_factory()() as s:
            resolver.resolve(s, rpc, self._context(s), head)
            self.forward = resolver.scoreboard(s)
            self.forward["paper_agent"] = resolver.paper_agent(s)
        self._prune(clock)
        with self._lock:
            self.last_run = datetime.now(timezone.utc).isoformat()
        self._save()

    def _context(self, s) -> tf.Context:
        if self._ctx is None or time.monotonic() - self._ctx_at > CONTEXT_REFRESH_SECONDS:
            self._ctx = tf.Context(s, CHAIN)
            self._ctx_at = time.monotonic()
        return self._ctx

    def _screen(self, rpc, due: list[Launch]) -> None:
        """Swaps by minute 5, for every due pool, in a few filtered queries."""
        lo = min(l.created_block for l in due)
        hi = max(l.created_block for l in due) + d.CUTOFF_BLOCKS
        counts: dict[str, int] = {l.pool: 0 for l in due}
        v4 = [l.pool for l in due if l.dex == "uniswap-v4"]
        v3 = [l.pool for l in due if l.dex == "uniswap-v3"]
        b = lo
        while b <= hi:
            top = min(b + rpc.log_span - 1, hi)
            for i in range(0, len(v4), 60):
                for log in rpc.get_logs(addresses=[UNISWAP_V4_POOL_MANAGER], from_block=b,
                                        to_block=top, topics=[V4_SWAP, v4[i:i + 60]]):
                    counts[(log.get("topics") or ["", ""])[1].lower()] = \
                        counts.get((log.get("topics") or ["", ""])[1].lower(), 0) + 1
            for i in range(0, len(v3), 60):
                for log in rpc.get_logs(addresses=v3[i:i + 60], from_block=b,
                                        to_block=top, topics=[V3_SWAP]):
                    counts[log["address"].lower()] = counts.get(log["address"].lower(), 0) + 1
            b = top + 1
        for l in due:
            l.swaps_by_cutoff = counts.get(l.pool, 0)
            if not l.swaps_by_cutoff:
                l.status = "not scored: no trades in the first 5 minutes"

    def _score(self, s, rpc, ctx: tf.Context, l: Launch, clock: d.Clock) -> None:
        cand = {"token_address": l.token, "quote_address": l.quote, "dex": l.dex,
                "pair_address": None if l.dex == "uniswap-v4" else l.pool,
                "pool_id": l.pool if l.dex == "uniswap-v4" else None,
                "created_block": l.created_block,
                "created_ts": datetime.fromisoformat(l.launch_ts)}
        ds_ingest.seed_tokens(s, [cand], chain=CHAIN, as_of_ts=datetime.now(timezone.utc))
        s.execute(text("""
            insert into token_sample (token_address, chain, sampling_stratum, pool_key, dex,
                created_block, launch_ts, screened, swaps_by_cutoff, excluded_reason, added_at)
            values (:t, :c, 'live', :pk, :dex, :cb, :lt, true, :sb,
                    'live: product scoring, not research', :now)
            on conflict (token_address, chain) do nothing
        """), {"t": l.token, "c": CHAIN, "pk": l.pool, "dex": l.dex, "cb": l.created_block,
               "lt": cand["created_ts"], "sb": l.swaps_by_cutoff,
               "now": datetime.now(timezone.utc)})
        s.commit()
        try:
            chain_ingest.backfill_token(
                s, rpc, rpc.budget, chain=CHAIN, token_address=l.token, quote_address=l.quote,
                start_block=l.created_block, pair_address=cand["pair_address"],
                pool_id=cand["pool_id"], quote_decimals=6 if l.quote in STABLES else 18,
                end_block=l.created_block + d.CUTOFF_BLOCKS)
            s.commit()
        except Exception as e:  # noqa: BLE001
            s.rollback()
            l.status = "not scored: could not read the first 5 minutes"
            l.notes.append(f"{type(e).__name__}: {str(e)[:120]}")
            return
        row = tf.token_row(s, ctx, token=l.token)
        if row is None:
            l.status = "not scored: no pool row"
            return
        l.launch_type = "launchpad" if row["r_mint_in_window"] else "self-deployed"
        l.buyers_by_cutoff = int(row["t_unique_buyers"])
        l.run_up_by_cutoff = float(2.718281828 ** row["t_log_price_drift"])
        if row["t_reserve_vs_peak"] <= d.RESERVE_FLOOR:
            l.status = "not scored: liquidity already pulled by minute 5"
            return
        x = [[float(row.get(n, 0.0) or 0.0) for n in self.meta["features"]]]
        self._features[l.token] = {n: float(row.get(n, 0.0) or 0.0) for n in self.meta["features"]}
        l.risk = float(self.model.predict_proba(x)[0, 1])
        l.status = "scored"
        l.scored_at = datetime.now(timezone.utc).isoformat()

    def _prune(self, clock: d.Clock) -> None:
        horizon = clock.head - KEEP_HOURS * 1800
        with self._lock:
            for k in [k for k, v in self.launches.items() if v.created_block < horizon]:
                del self.launches[k]

    # ---- reads ------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            items = sorted((asdict(v) for v in self.launches.values()),
                           key=lambda v: -v["created_block"])
            return {"model": self.meta, "forward": self.forward,
                    "scanned_to_block": self.scanned_to,
                    "last_run": self.last_run, "last_error": self.last_error,
                    "launches": items}

    def token(self, address: str) -> dict | None:
        l = self.launches.get(address.lower())
        return asdict(l) if l else None
