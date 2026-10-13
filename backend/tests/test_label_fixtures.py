"""Three hand-checked tokens, kept forever as a regression on the rules.

One whose liquidity was pulled, one that simply died, one that was still
trading at the end of its window. Each fixture holds the *observations* —
the reserve and price series actually sampled from Base — and the verdict a
human agreed with after reading them.

These are the tests that have to keep passing when a threshold moves. If a
future rule version reclassifies one of them, that is not necessarily a bug,
but it is a decision someone has to make on purpose rather than discover
later. The failure message says which token and which way it moved.

Regenerate with `python -m tests.record_label_fixtures` after agreeing with
the evidence that `python -m scripts.label show --token 0x...` prints.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from blocklens.label import build as lb
from blocklens.label import rules

FIXTURE = Path(__file__).parent / "fixtures" / "label_tokens.json"


def cases() -> list[dict]:
    if not FIXTURE.exists():
        return []
    return json.loads(FIXTURE.read_text(encoding="utf8"))["tokens"]


ALL = cases()


@pytest.mark.skipif(not ALL, reason="no label fixtures recorded yet")
def test_the_fixture_covers_the_three_outcomes_it_claims_to():
    """A fixture file that quietly lost its RUG case would make every test
    below pass while checking nothing interesting."""
    labels = {c["expected_label"] for c in ALL}
    assert "RUG" in labels, "no pulled-liquidity case in the fixtures"
    assert len(labels) >= 2, "the fixtures must cover more than one outcome"


@pytest.mark.parametrize("case", ALL, ids=[c["why"][:28] for c in ALL])
def test_hand_checked_token_keeps_its_label(case):
    series = lb.series_from({"series_json": case["series"]})
    m = rules.measure(series,
                      launch_ts=case["launch_ts"], end_ts=case["end_ts"],
                      sibling_pairs=case["sibling_pairs"],
                      swaps_in_window=case["swaps_in_window"])
    got = rules.classify(m)

    assert got.label == case["expected_label"], (
        f"{case['token_address']} was hand-checked as "
        f"{case['expected_label']} ({case['why']}) and now classifies as "
        f"{got.label}. Thresholds in force: {rules.thresholds()}"
    )


@pytest.mark.parametrize("case", ALL, ids=[c["why"][:28] for c in ALL])
def test_the_criterion_that_decided_it_is_the_one_we_expected(case):
    """Agreeing with a verdict for the wrong reason is still a bug: it would
    survive until the reason stopped holding."""
    series = lb.series_from({"series_json": case["series"]})
    m = rules.measure(series, launch_ts=case["launch_ts"], end_ts=case["end_ts"],
                      sibling_pairs=case["sibling_pairs"],
                      swaps_in_window=case["swaps_in_window"])
    got = rules.classify(m)

    for criterion, expected in case["expected_criteria"].items():
        assert getattr(got, criterion) is expected, (
            f"{case['token_address']}: expected {criterion}={expected}, "
            f"got {getattr(got, criterion)}"
        )


@pytest.mark.skipif(not ALL, reason="no label fixtures recorded yet")
def test_fixtures_carry_real_observations_not_placeholders():
    for case in ALL:
        pts = case["series"]
        assert len(pts) >= 9, f"{case['token_address']} has too few observations"
        assert any(p.get("r") is not None for p in pts), "no reserve readings"
        blocks = {p["b"] for p in pts}
        assert len(blocks) == len(pts), "duplicate blocks in a recorded series"
