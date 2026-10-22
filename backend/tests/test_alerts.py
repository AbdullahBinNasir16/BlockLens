"""Alerts fire only for the agent's own buy rule, and only when configured."""
from __future__ import annotations

import json

import httpx

from blocklens.live.alerts import Notifier
from blocklens.live.scorer import Launch


def _launch(**over) -> Launch:
    l = Launch(token="0x" + "ab" * 20, pool="0x" + "cd" * 20, dex="uniswap-v4",
               quote="0x" + "00" * 20, created_block=1, launch_ts="2026-10-22T00:00:00+00:00",
               status="scored", launch_type="launchpad", risk=0.05, swaps_by_cutoff=7,
               buyers_by_cutoff=5)
    for k, v in over.items():
        setattr(l, k, v)
    return l


def test_disabled_without_configuration_sends_nothing():
    n = Notifier(token="", chat_id="")
    assert not n.enabled
    assert n.send(_launch()) is False      # the transport block would fail a real call
    assert n.sent == 0


def test_should_alert_is_the_agents_buy_rule():
    n = Notifier(token="t", chat_id="c", max_risk=0.2)
    assert n.should_alert(_launch())
    assert not n.should_alert(_launch(risk=0.2))
    assert not n.should_alert(_launch(launch_type="self-deployed"))
    assert not n.should_alert(_launch(status="not scored: no trades in the first 5 minutes", risk=None))


def test_send_posts_to_the_bot_api_with_the_chat_and_the_token():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((str(req.url), json.loads(req.content)))
        return httpx.Response(200, json={"ok": True})

    n = Notifier(token="123:abc", chat_id="42", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert n.send(_launch()) is True
    url, body = calls[0]
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert body["chat_id"] == "42"
    assert "0x" + "ab" * 20 in body["text"] and "5%" in body["text"]
    assert n.sent == 1 and n.last_error is None


def test_a_failed_send_is_recorded_and_never_raises():
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"ok": False})

    n = Notifier(token="t", chat_id="c", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert n.send(_launch()) is False
    assert n.last_error and "HTTPStatusError" in n.last_error
