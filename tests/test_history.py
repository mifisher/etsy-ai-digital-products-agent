import json
import logging
from pathlib import Path

from radar.history import (
    append_decisions,
    load_previous_snapshot,
    recently_rejected,
    write_snapshot,
)
from radar.models import Candidate, ListingSnapshot


def _candidate(lane_id, verdict, score=0.2):
    return Candidate(
        niche="n",
        lane_id=lane_id,
        buyer="b",
        product_format="f",
        demand_signal={},
        competition_signal={},
        gap_ratio=0.1,
        price_range_usd=[10, 20],
        ease_to_create=0.5,
        differentiation_angle="d",
        why_this_could_sell="w",
        brand_fit="careeros",
        buildability="factory",
        quantitative=0.2,
        qualitative=0.2,
        score=score,
        verdict=verdict,
    )


def test_snapshot_round_trip(tmp_path: Path):
    snaps = [ListingSnapshot(1, "T", 6, 0, 19.0)]
    write_snapshot(tmp_path, "2026-08-04", snaps)

    previous = load_previous_snapshot(tmp_path, before="2026-08-11")

    assert previous[1]["views"] == 6


def test_load_previous_ignores_current_and_future_runs(tmp_path: Path):
    write_snapshot(tmp_path, "2026-08-04", [ListingSnapshot(1, "T", 6, 0, 19.0)])
    write_snapshot(tmp_path, "2026-08-11", [ListingSnapshot(1, "T", 30, 1, 19.0)])

    previous = load_previous_snapshot(tmp_path, before="2026-08-11")

    assert previous[1]["views"] == 6


def test_load_previous_returns_none_when_empty(tmp_path: Path):
    assert load_previous_snapshot(tmp_path, before="2026-08-04") is None


def test_rejected_lane_is_in_cooldown(tmp_path: Path):
    append_decisions(tmp_path, "2026-08-04", [_candidate("dead", "skip")])

    assert "dead" in recently_rejected(tmp_path, "2026-08-11", cooldown_days=30)


def test_cooldown_expires(tmp_path: Path):
    append_decisions(tmp_path, "2026-01-01", [_candidate("dead", "skip")])

    assert "dead" not in recently_rejected(tmp_path, "2026-08-11", cooldown_days=30)


def test_pursued_lane_is_not_suppressed(tmp_path: Path):
    append_decisions(tmp_path, "2026-08-04", [_candidate("good", "pursue", 0.9)])

    assert "good" not in recently_rejected(tmp_path, "2026-08-11", cooldown_days=30)


def test_recently_rejected_skips_malformed_line_but_honors_good_lines(
    tmp_path: Path,
):
    """A truncated/garbage line (e.g. from an interrupted Action run or a
    merge conflict marker) must not abort the whole read — the valid
    records before and after it must still be honored."""
    log = tmp_path / "decisions.jsonl"
    log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "date": "2026-08-01",
                        "lane_id": "first",
                        "niche": "n",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
                '{"date": "2026-08-02", "lane_id": "broken", "verd',  # truncated
                "<<<<<<< HEAD",  # merge conflict marker
                json.dumps(
                    {
                        "date": "2026-08-03",
                        "lane_id": "second",
                        "niche": "n",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rejected = recently_rejected(tmp_path, "2026-08-11", cooldown_days=30)

    assert "first" in rejected
    assert "second" in rejected
    assert "broken" not in rejected


def test_recently_rejected_logs_warning_on_malformed_line(tmp_path, caplog):
    log = tmp_path / "decisions.jsonl"
    log.write_text("not json at all\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="radar.history"):
        result = recently_rejected(tmp_path, "2026-08-11", cooldown_days=30)

    assert result == set()
    assert any("malformed" in rec.message.lower() for rec in caplog.records)
