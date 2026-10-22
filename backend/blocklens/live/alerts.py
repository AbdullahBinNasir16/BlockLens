"""Push a scored launch to someone who asked to be told.

One channel, Telegram, because its Bot API is free and keyless beyond the
bot's own token. The rule for *which* launches is the paper agent's buy
rule (DECISIONS.md, Phase 9): a launchpad launch, liquidity locked, with a
buyer-loss risk under the ceiling. Everything else stays on the page.

Off unless both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set, so the
API cannot message anyone by accident; and the send is best-effort, since a
failed alert must never stop the scorer.
"""
from __future__ import annotations

import httpx

from ..config import CONFIG

API = "https://api.telegram.org/bot{token}/sendMessage"


class Notifier:
    def __init__(self, *, token: str | None = None, chat_id: str | None = None,
                 max_risk: float | None = None, client: httpx.Client | None = None) -> None:
        self.token = CONFIG.telegram_bot_token if token is None else token
        self.chat_id = CONFIG.telegram_chat_id if chat_id is None else chat_id
        self.max_risk = CONFIG.alert_max_risk if max_risk is None else max_risk
        self._client = client
        self.sent = 0
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def should_alert(self, launch) -> bool:
        return (launch.status == "scored" and launch.launch_type == "launchpad"
                and launch.risk is not None and launch.risk < self.max_risk)

    def format(self, launch) -> str:
        risk = f"{launch.risk * 100:.0f}%" if launch.risk is not None else "—"
        return (
            f"BlockLens · new launchpad launch, buyer-loss risk {risk}\n"
            f"{launch.token}\n"
            f"{launch.dex.replace('uniswap-', 'Uniswap ')} · {launch.swaps_by_cutoff or 0} swaps, "
            f"{launch.buyers_by_cutoff or 0} buyers by minute 5\n"
            f"https://dexscreener.com/base/{launch.pool}\n"
            f"A model estimate at minute 5, not advice."
        )

    def send(self, launch) -> bool:
        """True if a message was accepted. False when disabled or on failure."""
        if not self.enabled:
            return False
        try:
            client = self._client or httpx.Client(timeout=10)
            r = client.post(API.format(token=self.token),
                            json={"chat_id": self.chat_id, "text": self.format(launch),
                                  "disable_web_page_preview": True})
            r.raise_for_status()
            self.sent += 1
            self.last_error = None
            return True
        except Exception as e:  # noqa: BLE001 - an alert must never stop the scorer
            self.last_error = f"{type(e).__name__}: {str(e)[:120]}"
            return False
