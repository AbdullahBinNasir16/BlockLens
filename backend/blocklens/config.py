"""Every tunable in one place, read from the environment with sane defaults.

Phase 1 runs on free, keyless sources. The Alchemy path exists but is off
unless a key is present, because the chain decision was explicitly "unpaid
work only" (see DECISIONS.md, 2026-10-11).
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class RateLimit:
    """A token bucket's shape: `rate` refills per second, up to `burst`."""
    rate: float
    burst: int


@dataclass(frozen=True)
class Config:
    # ---- store ----
    database_url: str = _str(
        "DATABASE_URL",
        "postgresql+psycopg://blocklens@127.0.0.1:5433/blocklens",
    )

    # ---- chain ----
    chain: str = _str("CHAIN", "base")
    # Measured in the Part A spike: 2.00 s/block exactly, 43,200 blocks a day.
    block_seconds: float = float(os.environ.get("BLOCK_SECONDS", "2.0"))
    feature_window_hours: int = _int("FEATURE_WINDOW_HOURS", 24)

    # ---- sources ----
    # Keyless. Measured cap: 1,000-block ranges, 20,000 results per call.
    rpc_url: str = _str("RPC_URL", "https://base.gateway.tenderly.co")
    rpc_log_span: int = _int("RPC_LOG_SPAN", 1_000)
    # A spare with a smaller cap, used only if the primary refuses.
    rpc_fallback_url: str = _str("RPC_FALLBACK_URL", "https://base.drpc.org")
    rpc_fallback_log_span: int = _int("RPC_FALLBACK_LOG_SPAN", 100)

    dexscreener_url: str = _str("DEXSCREENER_URL", "https://api.dexscreener.com")

    # Optional and off by default: set ALCHEMY_API_KEY to enable.
    alchemy_key: str = _str("ALCHEMY_API_KEY", "")
    alchemy_url_template: str = _str(
        "ALCHEMY_URL", "https://base-mainnet.g.alchemy.com/v2/{key}"
    )

    # ---- budgets ----
    # DexScreener documents 60/min on the pair endpoints and 300/min on
    # token-pairs; the lower one is used for both.
    limits: dict[str, RateLimit] = field(default_factory=lambda: {
        "dexscreener": RateLimit(rate=_int("DEXSCREENER_PER_MIN", 60) / 60.0, burst=5),
        # Public infrastructure we do not own: deliberately gentle. The spike
        # sustained ~1.4 req/s across 580 calls with zero errors.
        "rpc": RateLimit(rate=float(os.environ.get("RPC_PER_SEC", "4")), burst=4),
        "alchemy": RateLimit(rate=float(os.environ.get("ALCHEMY_PER_SEC", "15")), burst=15),
    })

    # Alchemy's monthly allowance. Only consumed when the Alchemy source is on.
    monthly_cu_ceiling: int = _int("MONTHLY_CU_CEILING", 30_000_000)
    # Published prices; unverified (no key in this environment).
    cu_get_asset_transfers: int = _int("CU_GET_ASSET_TRANSFERS", 120)
    cu_get_logs: int = _int("CU_GET_LOGS", 60)

    # A run that would exceed this stops cleanly and says so in ingest_run.
    default_max_calls_per_run: int = _int("MAX_CALLS_PER_RUN", 20_000)

    # ---- X / twitter ----
    # The only source in the project that can cost real money: ~half a US cent
    # per post read. Hard integer ceiling for the entire project.
    x_post_budget: int = _int("X_POST_BUDGET", 0)
    x_cache_dir: str = _str("X_CACHE_DIR", "data/x_cache")
    x_enabled: bool = os.environ.get("X_ENABLED", "0") == "1"

    # ---- alerts (Phase 10) ----
    # Off unless both are set. Telegram's Bot API is free; the only secret is
    # the bot's own token, which never enters the repository.
    telegram_bot_token: str = _str("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = _str("TELEGRAM_CHAT_ID", "")
    # The paper agent's buy ceiling (DECISIONS.md, Phase 9).
    alert_max_risk: float = float(os.environ.get("ALERT_MAX_RISK", "0.2"))

    @property
    def alchemy_enabled(self) -> bool:
        return bool(self.alchemy_key)

    @property
    def alchemy_url(self) -> str:
        return self.alchemy_url_template.format(key=self.alchemy_key)

    @property
    def blocks_per_window(self) -> int:
        return int(self.feature_window_hours * 3600 / self.block_seconds)


def git_sha() -> str:
    """Stamped onto every ingest_run so a row can be traced to the code."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - never block ingestion on git
        return "unknown"


CONFIG = Config()
