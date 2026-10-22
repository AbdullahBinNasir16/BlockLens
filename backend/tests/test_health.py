"""Every status the scorer writes folds into a named reason."""
from blocklens.live.health import REASONS, reason_of


def test_every_scorer_status_has_a_reason():
    statuses = [
        "scored",
        "not scored: no trades in the first 5 minutes",
        "not scored: liquidity already pulled by minute 5",
        "not scored: pool initialised at an untradeable price",
        "not scored: missed during an outage (past its 6-hour mark)",
        "not scored: could not read the first 5 minutes",
        "not scored: trades settled without token transfers",
    ]
    for st in statuses:
        assert reason_of(st) != "other", st
    assert reason_of("not scored: something new") == "other"
    assert len({label for _, label in REASONS}) == len(REASONS)
