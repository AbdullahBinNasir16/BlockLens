"""HTTP access to the outside world. Explicit timeouts, explicit retries.

No module outside this one makes a network call to a metered API, and
every call here passes through the budget first.

Phase 1 runs keyless: the chain comes from a public RPC gateway, market
state from DexScreener. The Alchemy source exists and is tested, but is
inert unless ALCHEMY_API_KEY is set — see DECISIONS.md, 2026-10-11.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import httpx

from ..config import CONFIG, Config
from .budget import Budget

TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=15.0, pool=10.0)
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class SourceError(RuntimeError):
    pass


class Source:
    """Shared retry/backoff behaviour. Subclasses declare `name`, which is
    the budget bucket they draw from."""

    name = "source"

    def __init__(self, budget: Budget, client: httpx.Client | None = None,
                 config: Config = CONFIG, retries: int = 3):
        self.budget = budget
        self.config = config
        self.retries = retries
        self._client = client or httpx.Client(timeout=TIMEOUT, headers={
            "user-agent": "blocklens/0.1 (+phase1 research pipeline)",
            "accept": "application/json",
        })

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, url: str, *, cu: int = 0, **kw) -> Any:
        last: Exception | None = None
        for attempt in range(self.retries):
            self.budget.charge(self.name, cu=cu)
            try:
                r = self._client.request(method, url, **kw)
                if r.status_code in RETRY_STATUS:
                    last = SourceError(f"{r.status_code} from {url}: {r.text[:160]}")
                    time.sleep(0.4 * (2 ** attempt))
                    continue
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as e:
                last = e
                time.sleep(0.4 * (2 ** attempt))
        raise SourceError(f"{self.name}: {method} {url} failed after {self.retries}: {last}")


class RpcSource(Source):
    """JSON-RPC against a public gateway.

    Measured in Part A: 1,000-block ranges and 20,000 results per call on
    the default endpoint. Both limits are config, not constants, because
    they are the single most load-bearing number in the cost model.
    """

    name = "rpc"

    def __init__(self, budget: Budget, client: httpx.Client | None = None,
                 config: Config = CONFIG, url: str | None = None,
                 log_span: int | None = None):
        super().__init__(budget, client, config)
        self.url = url or config.rpc_url
        self.log_span = log_span or config.rpc_log_span

    def call(self, method: str, params: list, *, cu: int = 0) -> Any:
        body = self._request("POST", self.url, cu=cu,
                             json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if isinstance(body, dict) and "error" in body:
            raise SourceError(f"rpc {method}: {body['error']}")
        return body.get("result") if isinstance(body, dict) else None

    def batch(self, calls: Sequence[tuple[str, list]], *, size: int = 20) -> list[Any]:
        """Several calls in one JSON-RPC batch request, results in order.

        Throughput on the keyless gateway is bounded by round-trip latency,
        not by its rate limit (Phase 1 measured that raising the bucket from
        4 to 10 req/s changed nothing). A batch of 20 returns in ~1.4 s
        against ~0.47 s per serial call, measured 2026-10-18. Every call in
        a batch is still charged to the budget and the token bucket one by
        one, so the per-call rate ceiling holds exactly as before; only the
        number of HTTP requests falls.

        A failed call comes back as a `SourceError` in its slot rather than
        raising, so one revert does not discard its neighbours - the same
        contract `Sampler.point` relies on for single calls.
        """
        out: list[Any] = []
        for i in range(0, len(calls), size):
            chunk = calls[i:i + size]
            body = [{"jsonrpc": "2.0", "id": k, "method": m, "params": p}
                    for k, (m, p) in enumerate(chunk)]
            for _ in chunk[1:]:
                # the first charge happens inside _request
                self.budget.charge(self.name)
            res = self._request("POST", self.url, json=body)
            if not isinstance(res, list):
                err = SourceError(f"rpc batch: unexpected reply {str(res)[:160]}")
                out.extend([err] * len(chunk))
                continue
            by_id = {r.get("id"): r for r in res if isinstance(r, dict)}
            for k, (m, _p) in enumerate(chunk):
                r = by_id.get(k)
                if r is None:
                    out.append(SourceError(f"rpc {m}: missing from batch reply"))
                elif "error" in r:
                    out.append(SourceError(f"rpc {m}: {r['error']}"))
                else:
                    out.append(r.get("result"))
        return out

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def get_block(self, number: int) -> dict:
        return self.call("eth_getBlockByNumber", [hex(number), False])

    def get_logs(self, *, addresses: Sequence[str] | None = None, from_block: int, to_block: int,
                 topics: list | None = None, cu: int = 0) -> list[dict]:
        f: dict[str, Any] = {"fromBlock": hex(from_block), "toBlock": hex(to_block)}
        if addresses:
            f["address"] = [a.lower() for a in addresses] if len(addresses) > 1 else addresses[0].lower()
        if topics:
            f["topics"] = topics
        return self.call("eth_getLogs", [f], cu=cu) or []

    def block_at_timestamp(self, ts: int) -> int:
        """First block at or after `ts`, by binary search over block times."""
        hi = self.block_number()
        lo = max(1, hi - 25_000_000)
        while lo < hi:
            mid = (lo + hi) // 2
            b = self.get_block(mid)
            if b is None:
                hi = mid - 1
                continue
            if int(b["timestamp"], 16) < ts:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def block_timestamps(self, numbers: Iterable[int]) -> dict[int, int]:
        """Block -> unix seconds. Cached per instance: a token-day touches
        far fewer distinct blocks than it has logs."""
        if not hasattr(self, "_ts_cache"):
            self._ts_cache: dict[int, int] = {}
        out = {}
        for n in numbers:
            if n not in self._ts_cache:
                b = self.get_block(n)
                self._ts_cache[n] = int(b["timestamp"], 16) if b else 0
            out[n] = self._ts_cache[n]
        return out


@dataclass
class Endpoint:
    """One keyless provider, paced on its own."""
    url: str
    batch: int                    # largest batch it accepts; 1 = no batching
    logs: bool                    # serves 1,000-block eth_getLogs
    interval: float = 1.0         # seconds between HTTP requests to it
    next_at: float = 0.0
    cool_until: float = 0.0
    strikes: int = 0
    calls: int = 0
    errors: int = 0


# Measured 2026-10-18 (Phase 5): archive eth_call at -200 days answered by
# all four; batches of 8 accepted by the first two; 1,000-block getLogs only
# by Tenderly. Tenderly rate-limits per call inside a batch, so it gets
# single calls only.
DEFAULT_POOL = (
    Endpoint("https://mainnet.base.org", batch=8, logs=False),
    Endpoint("https://base-mainnet.public.blastapi.io", batch=8, logs=False),
    Endpoint("https://base.gateway.tenderly.co", batch=1, logs=True, interval=0.3),
    Endpoint("https://base.drpc.org", batch=1, logs=False, interval=0.5),
)


class PooledRpcSource(RpcSource):
    """The same interface as `RpcSource`, over several keyless providers.

    Phase 5 needs ~400k archive reads. One gateway, politely paced, is a
    two-day job; four, each paced at no more than one HTTP request a second
    and backing off on its own 429s, are an afternoon. No provider sees more
    load than the single-gateway design gave Tenderly alone.

    Every call is still charged to the run budget one by one.
    """

    name = "rpc"

    def __init__(self, budget: Budget, pool: Sequence[Endpoint] = DEFAULT_POOL,
                 config: Config = CONFIG):
        super().__init__(budget, config=config)
        self.pool = [Endpoint(**{k: getattr(e, k) for k in
                                 ("url", "batch", "logs", "interval")}) for e in pool]
        self._rr = 0

    # ---- endpoint choice -------------------------------------------------

    def _pick(self, *, need_logs: bool = False, min_batch: int = 1) -> Endpoint:
        while True:
            now = time.monotonic()
            ok = [e for e in self.pool if e.cool_until <= now
                  and (e.logs or not need_logs) and e.batch >= min_batch]
            if not ok:
                ok = [e for e in self.pool if (e.logs or not need_logs)]
                wake = min(max(e.cool_until, e.next_at) for e in ok)
                time.sleep(max(0.05, wake - now))
                continue
            ready = [e for e in ok if e.next_at <= now]
            if ready:
                self._rr += 1
                e = ready[self._rr % len(ready)]
                e.next_at = now + e.interval
                return e
            time.sleep(max(0.02, min(e.next_at for e in ok) - now))

    def _post(self, e: Endpoint, body: Any) -> Any:
        try:
            r = self._client.post(e.url, json=body)
        except httpx.HTTPError as ex:
            e.errors += 1
            e.cool_until = time.monotonic() + 10
            raise SourceError(f"{e.url}: {ex}") from ex
        limited = r.status_code == 429 or (
            r.status_code == 200 and isinstance(body, dict)
            and '"code":-32005' in r.text.replace(" ", ""))
        if limited or r.status_code in RETRY_STATUS:
            e.strikes += 1
            e.errors += 1
            e.cool_until = time.monotonic() + min(120, 15 * e.strikes)
            if e.batch > 2:
                e.batch = max(2, e.batch // 2)
            raise _Retry(f"{r.status_code} from {e.url}")
        e.strikes = max(0, e.strikes - 1)
        try:
            return r.json()
        except ValueError as ex:
            e.errors += 1
            e.cool_until = time.monotonic() + 30
            raise _Retry(f"non-JSON from {e.url}") from ex

    # ---- the RpcSource interface -----------------------------------------

    def call(self, method: str, params: list, *, cu: int = 0) -> Any:
        need_logs = method == "eth_getLogs"
        # Logs have one capable endpoint, so a refusal means waiting it out
        # rather than failing over; give them a much longer budget.
        for _ in range(40 if need_logs else 8):
            self.budget.charge(self.name, cu=cu)
            e = self._pick(need_logs=need_logs)
            try:
                body = self._post(e, {"jsonrpc": "2.0", "id": 1,
                                      "method": method, "params": params})
            except (_Retry, SourceError):
                # a timeout or refusal cools that endpoint; try the next
                continue
            e.calls += 1
            if isinstance(body, dict) and "error" in body:
                err = str(body["error"])
                if any(k in err for k in ("rate", "limit", "pruned", "Archive")):
                    e.cool_until = time.monotonic() + 30
                    continue
                raise SourceError(f"rpc {method}: {body['error']}")
            return body.get("result") if isinstance(body, dict) else None
        raise SourceError(f"rpc {method}: every endpoint refused, retries exhausted")

    def batch(self, calls: Sequence[tuple[str, list]], *, size: int = 20) -> list[Any]:
        out: list[Any] = [None] * len(calls)
        todo = list(range(len(calls)))
        # Bounded by *failed* attempts. An earlier version bounded every
        # sub-batch, so a 320-call dense pass (41 batches of 8) silently lost
        # its tail as "not served" - caught in the first six Phase 5 labels.
        failures = 0
        while todo and failures < 60:
            e = self._pick()
            n = max(1, min(e.batch, size, len(todo)))
            idx, todo = todo[:n], todo[n:]
            for _ in idx:
                self.budget.charge(self.name)
            if n == 1:
                k = idx[0]
                m, p = calls[k]
                body_one = {"jsonrpc": "2.0", "id": 0, "method": m, "params": p}
                try:
                    res = self._post(e, body_one)
                except (_Retry, SourceError):
                    failures += 1
                    todo = idx + todo
                    continue
                res = [res]
            else:
                body = [{"jsonrpc": "2.0", "id": j, "method": calls[k][0],
                         "params": calls[k][1]} for j, k in enumerate(idx)]
                try:
                    res = self._post(e, body)
                except (_Retry, SourceError):
                    failures += 1
                    todo = idx + todo
                    continue
            if not isinstance(res, list):
                failures += 1
                todo = idx + todo
                e.cool_until = time.monotonic() + 20
                continue
            e.calls += n
            by_id = {r.get("id"): r for r in res if isinstance(r, dict)}
            retry: list[int] = []
            for j, k in enumerate(idx):
                r = by_id.get(j if n > 1 else 0)
                if r is None:
                    retry.append(k)
                elif "error" in r:
                    err = str(r["error"])
                    if any(w in err for w in ("rate", "limit", "pruned", "Archive")):
                        retry.append(k)
                    else:
                        out[k] = SourceError(f"rpc {calls[k][0]}: {r['error']}")
                else:
                    out[k] = r.get("result")
            if retry:
                failures += 1
                e.cool_until = time.monotonic() + 15
                todo = retry + todo
        for k in todo:
            out[k] = SourceError("rpc batch: not served after retries")
        return out

    def stats(self) -> list[dict]:
        return [{"url": e.url, "calls": e.calls, "errors": e.errors, "batch": e.batch}
                for e in self.pool]


class _Retry(Exception):
    """An endpoint refused for a reason another endpoint will not share."""


class DexScreenerSource(Source):
    """Keyless, 60 requests a minute on the documented endpoints."""

    name = "dexscreener"

    def search(self, q: str) -> list[dict]:
        d = self._request("GET", f"{self.config.dexscreener_url}/latest/dex/search", params={"q": q})
        return (d or {}).get("pairs") or []

    def token_pairs(self, chain: str, token: str) -> list[dict]:
        d = self._request("GET", f"{self.config.dexscreener_url}/token-pairs/v1/{chain}/{token}")
        return d if isinstance(d, list) else []

    def tokens_batch(self, chain: str, addresses: Sequence[str]) -> list[dict]:
        """Up to 30 addresses per call — 30x cheaper than asking one at a
        time, which matters when classifying a thousand candidates."""
        if not addresses:
            return []
        joined = ",".join(addresses[:30])
        d = self._request("GET", f"{self.config.dexscreener_url}/tokens/v1/{chain}/{joined}")
        return d if isinstance(d, list) else []


class AlchemySource(Source):
    """Optional. Inert without a key; the project runs unpaid by default."""

    name = "alchemy"

    @property
    def enabled(self) -> bool:
        return self.config.alchemy_enabled

    def get_asset_transfers(self, *, contract: str, from_block: int, to_block: int,
                            page_key: str | None = None, max_count: int = 1000) -> dict:
        if not self.enabled:
            raise SourceError("alchemy source is disabled: no ALCHEMY_API_KEY")
        params: dict[str, Any] = {
            "fromBlock": hex(from_block), "toBlock": hex(to_block),
            "category": ["erc20"], "contractAddresses": [contract],
            "maxCount": hex(max_count), "withMetadata": True,
        }
        if page_key:
            params["pageKey"] = page_key
        body = self._request(
            "POST", self.config.alchemy_url, cu=self.config.cu_get_asset_transfers,
            json={"jsonrpc": "2.0", "id": 1, "method": "alchemy_getAssetTransfers",
                  "params": [params]},
        )
        if "error" in body:
            raise SourceError(f"alchemy: {body['error']}")
        return body.get("result") or {}
