"""X (Twitter) search — built, tested, and switched off.

This is the only source in the project that can spend real money, so it is
the one source that cannot run by accident. Three locks, all of which must
be opened deliberately:

1. `X_ENABLED` is not set, so `fetch` refuses before it builds a request.
2. `X_POST_BUDGET` defaults to **0** posts. The ceiling is an integer count
   of posts for the whole project, spent from a ledger in the database, so
   a restart cannot forget what has already been spent.
3. Nothing calls it. No CLI command reaches this module in Phase 1.

It is cache-first by design rather than as an optimisation: a cached
response is replayed without a request, which is also how the tests run
against a recorded fixture with no network at all.

Per the brief: do not run this in Phase 1.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..config import CONFIG, Config
from ..store import write
from .budget import Budget, BudgetExhausted
from .sources import Source

SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
FIELDS = "created_at,public_metrics,author_id,entities"


class XDisabled(RuntimeError):
    """The switch is off. Not an error condition — the default state."""


def cache_key(query: str, *, max_results: int) -> str:
    raw = f"{query}|{max_results}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


class XSource(Source):
    """Recent-search against the X API v2, or the cache standing in for it."""

    name = "x"

    def __init__(self, budget: Budget, client: httpx.Client | None = None,
                 config: Config = CONFIG, cache_dir: str | Path | None = None,
                 bearer: str | None = None):
        super().__init__(budget, client, config)
        self.cache_dir = Path(cache_dir or config.x_cache_dir)
        self.bearer = bearer if bearer is not None else os.environ.get("X_BEARER_TOKEN", "")

    # ---- cache -----------------------------------------------------------

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def cached(self, query: str, *, max_results: int = 10) -> dict | None:
        p = self._path(cache_key(query, max_results=max_results))
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf8"))

    def _store(self, key: str, payload: dict) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(json.dumps(payload, indent=1), encoding="utf8")

    # ---- the one entry point --------------------------------------------

    def search(self, session: Session | None, query: str, *, max_results: int = 10,
               allow_network: bool = False) -> dict:
        """A cached response always; a live one only if every lock is open.

        `session` is required for a live call and may be None for a cache
        read, because spending has to be recorded durably and counting
        nothing needs no ledger.
        """
        key = cache_key(query, max_results=max_results)
        hit = self.cached(query, max_results=max_results)
        if hit is not None:
            return {**hit, "_cache": "hit"}

        if not allow_network or not self.config.x_enabled:
            raise XDisabled(
                "x source is off: pass allow_network=True and set X_ENABLED=1. "
                "Phase 1 does not run it at all."
            )
        if not self.bearer:
            raise XDisabled("x source has no X_BEARER_TOKEN")
        if session is None:
            raise ValueError("a live x call needs a session to record its spend")

        period = Budget.period()
        _, spent = write.read_budget(session, source="x", period=period)
        ceiling = self.config.x_post_budget
        if spent + max_results > ceiling:
            raise BudgetExhausted(
                f"x post budget would be crossed: {spent} + {max_results} > {ceiling} "
                f"posts for {period}. Raise X_POST_BUDGET deliberately or stop."
            )

        payload = self._request(
            "GET", SEARCH_URL,
            params={"query": query, "max_results": max_results, "tweet.fields": FIELDS},
            headers={"authorization": f"Bearer {self.bearer}"},
        )
        # Posts actually returned, not posts requested: the ledger records
        # what was spent, and a thin result costs less than a full page.
        returned = len((payload or {}).get("data") or [])
        write.bump_budget(session, source="x", period=period,
                          requests=1, compute_units=returned)
        session.commit()
        self._store(key, payload)
        return {**payload, "_cache": "miss"}


def posts_from(payload: dict) -> list[dict]:
    """Flatten a search response into rows. Pure, so it is what the fixture
    test exercises — no network, no database, no switch to open."""
    out = []
    for post in (payload or {}).get("data") or []:
        m = post.get("public_metrics") or {}
        created = post.get("created_at")
        out.append({
            "post_id": post.get("id"),
            "author_id": post.get("author_id"),
            "text": post.get("text"),
            "created_ts": (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created else None
            ),
            "likes": m.get("like_count"),
            "reposts": m.get("retweet_count"),
            "replies": m.get("reply_count"),
            "cashtags": sorted({
                (c.get("tag") or "").upper()
                for c in ((post.get("entities") or {}).get("cashtags") or [])
            }),
            "provenance": "live",
        })
    return out


def spend_report(session: Session, *, config: Config = CONFIG) -> dict[str, Any]:
    period = Budget.period()
    requests, posts = write.read_budget(session, source="x", period=period)
    return {
        "period": period, "requests": requests, "posts": posts,
        "ceiling": config.x_post_budget,
        "enabled": config.x_enabled,
        "remaining": max(0, config.x_post_budget - posts),
        "utc_now": datetime.now(timezone.utc),
    }
