import pytest

from radar.collectors import collect_lane_signals, snapshot_own_listings, diagnose
from radar.config import Lane


def _listing(fav, price_cents, title="t"):
    return {
        "title": title,
        "num_favorers": fav,
        "price": {"amount": price_cents, "divisor": 100},
    }


def test_collect_lane_signals_uses_mean_favorites_and_median_price():
    """Regression: favorites are heavy-tailed (mostly zero, occasional viral
    listing), so the demand signal must be the mean, not the median — a
    real 5-listing sample was [0, 0, 34, 1475, 470], whose median (34)
    erases almost all of the signal the mean (395.8) preserves. Price is
    tightly clustered, so it stays a median (robust to a single outlier)."""

    def fake_fetch(url, headers):
        return {
            "count": 500,
            "results": [
                _listing(0, 1000, "a"),
                _listing(0, 2000, "b"),
                _listing(34, 3000, "c"),
                _listing(1475, 1500, "d"),
                _listing(470, 2500, "e"),
            ],
        }

    from radar.etsy_api import EtsyPublicClient

    client = EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)
    lane = Lane(id="x", keywords=["kw"], credibility=0.9, brand_fit="careeros")

    sig = collect_lane_signals(client, lane, limit=5)

    assert sig.active_listings == 500
    assert sig.mean_favorites == pytest.approx(395.8)
    assert sig.median_price == 20.0
    assert sig.sample_size == 5
    assert sig.sample_titles == ["a", "b", "c", "d", "e"]


def test_collect_lane_signals_handles_empty_results():
    def fake_fetch(url, headers):
        return {"count": 0, "results": []}

    from radar.etsy_api import EtsyPublicClient

    client = EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)
    lane = Lane(id="x", keywords=["kw"], credibility=0.5, brand_fit="new_shop")

    sig = collect_lane_signals(client, lane, limit=5)

    assert sig.active_listings == 0
    assert sig.mean_favorites == 0.0
    assert sig.median_price == 0.0
    assert sig.sample_size == 0


def test_snapshot_and_diagnose():
    def fake_fetch(url, headers):
        return {
            "results": [
                {
                    "listing_id": 1,
                    "title": "T",
                    "views": 6,
                    "num_favorers": 0,
                    "price": {"amount": 1900, "divisor": 100},
                }
            ]
        }

    from radar.etsy_api import EtsyPublicClient

    client = EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)
    snaps = snapshot_own_listings(client, "12345678")

    assert snaps[0].views == 6
    assert snaps[0].price_usd == 19.0
    assert diagnose(snaps[0]) == "invisible"


def test_diagnose_seen_but_not_wanted():
    from radar.collectors import ListingSnapshot

    snap = ListingSnapshot(
        listing_id=2, title="T", views=250, favorites=0, price_usd=19.0
    )
    assert diagnose(snap) == "seen_not_wanted"
