from pathlib import Path

from radar.config import Config, Lane
from radar.etsy_api import EtsyPublicClient
from radar.run import run_radar

CONFIG = Config(
    shop_id="YOUR_ETSY_SHOP_ID",
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
