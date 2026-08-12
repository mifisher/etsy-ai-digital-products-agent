import json
import logging
from pathlib import Path

from radar.config import Config, Lane
from radar.etsy_api import EtsyPublicClient
from radar.models import Judgment
from radar.run import _build_judge, run_radar

CONFIG = Config(
    shop_id="12345678",
    lanes=[
        Lane(id="a", keywords=["kw a"], credibility=0.9, brand_fit="careeros"),
        Lane(id="b", keywords=["kw b"], credibility=0.5, brand_fit="new_shop"),
    ],
    weights={
        "quantitative": {"demand": 0.40, "gap": 0.40, "price": 0.20},
        "qualitative": {
            "pain_urgency": 0.30,
            "willingness_to_pay": 0.30,
            "differentiation": 0.25,
            "credibility": 0.15,
        },
        "final": {"quantitative": 0.45, "qualitative": 0.35, "ease_to_create": 0.20},
    },
    thresholds={"pursue": 0.65, "maybe": 0.40},
    limits={"search_limit": 5, "reject_cooldown_days": 30},
)


def _client():
    def fake_fetch(url, headers):
        if "/shops/" in url:
            return {
                "results": [
                    {
                        "listing_id": 4532224344,
                        "title": "AI Job Search",
                        "views": 6,
                        "num_favorers": 0,
                        "price": {"amount": 1900, "divisor": 100},
                    }
                ]
            }
        return {
            "count": 300,
            "results": [
                {
                    "title": "Competitor",
                    "num_favorers": 50,
                    "price": {"amount": 1500, "divisor": 100},
                }
            ],
        }

    return EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)


def test_run_writes_digest_and_history(tmp_path: Path):
    markdown, path = run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=lambda lane, sig: None
    )

    assert "Opportunity Radar — 2026-08-04" in markdown
    assert path is not None and path.exists()
    assert (tmp_path / "snapshots" / "2026-08-04.json").exists()
    assert (tmp_path / "decisions.jsonl").exists()


def test_run_dry_run_writes_nothing(tmp_path: Path):
    markdown, path = run_radar(
        CONFIG,
        _client(),
        "2026-08-04",
        tmp_path,
        judge=lambda lane, sig: None,
        dry_run=True,
    )

    assert markdown
    assert path is None
    assert not (tmp_path / "snapshots").exists()


def test_run_skips_lanes_in_rejection_cooldown(tmp_path: Path):
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions.jsonl").write_text(
        '{"date": "2026-08-01", "lane_id": "b", "niche": "kw b",'
        ' "score": 0.1, "verdict": "skip"}\n',
        encoding="utf-8",
    )

    markdown, _ = run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=lambda lane, sig: None
    )

    assert "kw a" in markdown
    assert "kw b" not in markdown


THREE_LANE_CONFIG = Config(
    shop_id="12345678",
    lanes=[
        Lane(id="a", keywords=["kw a"], credibility=0.9, brand_fit="careeros"),
        Lane(id="b", keywords=["kw b"], credibility=0.5, brand_fit="new_shop"),
        Lane(id="c", keywords=["kw c"], credibility=0.5, brand_fit="new_shop"),
    ],
    weights=CONFIG.weights,
    thresholds=CONFIG.thresholds,
    limits={"search_limit": 5, "reject_cooldown_days": 30},
)


def _three_lane_client():
    """Distinct signals per lane: 'a' is the minimum on every metric, so if
    it were the ONLY lane in the normalization pool, log_minmax's
    degenerate single-value branch would score every component 0.5. Scored
    against the full 3-lane pool, 'a' is the minimum and normalizes to 0.0
    on every component instead."""

    per_keyword = {
        "kw+a": (10, 1000),  # (favorites, price cents)
        "kw+b": (50, 2000),
        "kw+c": (100, 3000),
    }

    def fake_fetch(url, headers):
        if "/shops/" in url:
            return {"results": []}
        for kw, (favorites, price_cents) in per_keyword.items():
            if f"keywords={kw}" in url:
                return {
                    "count": 300,
                    "results": [
                        {
                            "title": "Competitor",
                            "num_favorers": favorites,
                            "price": {"amount": price_cents, "divisor": 100},
                        }
                    ],
                }
        raise AssertionError(f"unexpected url: {url}")

    return EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)


def test_cooldown_survivor_scored_against_full_normalization_pool(tmp_path: Path):
    """FIX 1: cooling down all lanes but one must not collapse the pool the
    survivor is normalized against. Filtering must happen on the results,
    after collection and scoring, not before."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "date": "2026-08-01",
                        "lane_id": "b",
                        "niche": "kw b",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
                json.dumps(
                    {
                        "date": "2026-08-01",
                        "lane_id": "c",
                        "niche": "kw c",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    markdown, _ = run_radar(
        THREE_LANE_CONFIG,
        _three_lane_client(),
        "2026-08-04",
        tmp_path,
        judge=lambda lane, sig: None,
    )

    assert "kw a" in markdown
    assert "kw b" not in markdown
    assert "kw c" not in markdown

    # 'a' is the minimum on every quantitative metric across the full
    # 3-lane pool, so its normalized quant score is exactly 0.0 — not the
    # degenerate 0.5 a single-lane pool would produce.
    row = next(line for line in markdown.splitlines() if line.startswith("| kw a"))
    fields = [f.strip() for f in row.split("|")]
    score = fields[2]
    assert score == "0.00", f"expected degenerate-pool bug absent, got score={score}"


def test_cooldown_does_not_write_new_decision_for_suppressed_lane(tmp_path: Path):
    """A lane suppressed by the cooldown must not get a fresh 'skip'
    appended to decisions.jsonl, or its cooldown would renew forever and it
    could never come back."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions.jsonl").write_text(
        json.dumps(
            {
                "date": "2026-08-01",
                "lane_id": "b",
                "niche": "kw b",
                "score": 0.1,
                "verdict": "skip",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=lambda lane, sig: None
    )

    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    b_records = [r for r in records if r["lane_id"] == "b"]

    # Only the original seeded record — no new one appended this run.
    assert len(b_records) == 1
    assert b_records[0]["date"] == "2026-08-01"


def test_lane_escapes_cooldown_after_expiry(tmp_path: Path):
    """A cooled-down lane must resurface once the cooldown window passes —
    the suppression must not be permanent."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions.jsonl").write_text(
        json.dumps(
            {
                "date": "2026-01-01",
                "lane_id": "b",
                "niche": "kw b",
                "score": 0.1,
                "verdict": "skip",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    markdown, _ = run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=lambda lane, sig: None
    )

    assert "kw b" in markdown


def test_cooled_lane_judgment_failure_does_not_warn_about_visible_table(
    tmp_path: Path,
):
    """A lane's judgment failure only matters for the warning banner if
    that lane is actually shown in the digest. A cooled-down lane that
    failed judgment must not trigger a false 'quantitative-only' warning
    about a visible table that was, in fact, fully judged."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "decisions.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "date": "2026-08-01",
                        "lane_id": "b",
                        "niche": "kw b",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
                json.dumps(
                    {
                        "date": "2026-08-01",
                        "lane_id": "c",
                        "niche": "kw c",
                        "score": 0.1,
                        "verdict": "skip",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    judgment = Judgment(
        pain_urgency=0.8,
        willingness_to_pay=0.7,
        differentiation=0.6,
        ease_to_create=0.9,
        buildability="factory",
        buyer="Solo consultants",
        product_format="Google Sheets + PDF",
        differentiation_angle="angle",
        why_this_could_sell="reasons",
        price_range_usd=[12, 29],
    )

    # Only lane 'a' (the visible one) gets judged; the cooled-down 'b' and
    # 'c' fail judgment — but they never appear in the digest table.
    def judge(lane, sig):
        return judgment if lane.id == "a" else None

    markdown, _ = run_radar(
        THREE_LANE_CONFIG,
        _three_lane_client(),
        "2026-08-04",
        tmp_path,
        judge=judge,
    )

    assert "kw a" in markdown
    assert "quantitative-only" not in markdown.lower()


def test_partial_llm_judgment_warns_with_counts(tmp_path: Path):
    """FIX 5: if only some evaluated lanes got an LLM judgment, the digest
    must warn (not silently mix judged and unjudged scores) and state how
    many of N lanes were judged."""

    judgment = Judgment(
        pain_urgency=0.8,
        willingness_to_pay=0.7,
        differentiation=0.6,
        ease_to_create=0.9,
        buildability="factory",
        buyer="Solo consultants",
        product_format="Google Sheets + PDF",
        differentiation_angle="angle",
        why_this_could_sell="reasons",
        price_range_usd=[12, 29],
    )

    def judge(lane, sig):
        return judgment if lane.id == "a" else None

    markdown, _ = run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=judge
    )

    assert "1/2 lanes judged" in markdown
    assert "quantitative-only" in markdown.lower()


def test_build_judge_logs_warning_and_falls_back_when_llm_unusable(
    monkeypatch, caplog
):
    """FIX 4: _build_judge's fallback to a no-op judge must be logged, not
    silent, while still degrading gracefully (never raising)."""
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ETSY_LLM_PROVIDER", raising=False)

    with caplog.at_level(logging.WARNING, logger="radar.run"):
        judge = _build_judge()

    lane = CONFIG.lanes[0]
    assert judge(lane, None) is None
    assert any(
        "llm" in rec.message.lower() and "unavailable" in rec.message.lower()
        for rec in caplog.records
    )


def test_full_llm_judgment_does_not_warn(tmp_path: Path):
    judgment = Judgment(
        pain_urgency=0.8,
        willingness_to_pay=0.7,
        differentiation=0.6,
        ease_to_create=0.9,
        buildability="factory",
        buyer="Solo consultants",
        product_format="Google Sheets + PDF",
        differentiation_angle="angle",
        why_this_could_sell="reasons",
        price_range_usd=[12, 29],
    )

    markdown, _ = run_radar(
        CONFIG, _client(), "2026-08-04", tmp_path, judge=lambda lane, sig: judgment
    )

    assert "quantitative-only" not in markdown.lower()
