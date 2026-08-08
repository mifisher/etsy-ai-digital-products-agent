from radar.collectors import collect_lane_signals, snapshot_own_listings, diagnose
from radar.config import Lane


def _listing(fav, price_cents, title="t"):
    return {
        "title": title,
        "num_favorers": fav,
        "price": {"amount": price_cents, "divisor": 100},
    }


def test_collect_lane_signals_uses_medians_and_total_count():
    def fake_fetch(url, headers):
        return {
            "count": 500,
            "results": [
                _listing(10, 1000, "a"),
                _listing(20, 2000, "b"),
                _listing(30, 3000, "c"),
            ],
        }

    from radar.etsy_api import EtsyPublicClient

    client = EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)
    lane = Lane(id="x", keywords=["kw"], credibility=0.9, brand_fit="careeros")

    sig = collect_lane_signals(client, lane, limit=3)

    assert sig.active_listings == 500
    assert sig.median_favorites == 20
    assert sig.median_price == 20.0
    assert sig.sample_size == 3
    assert sig.sample_titles == ["a", "b", "c"]


def test_collect_lane_signals_handles_empty_results():
    def fake_fetch(url, headers):
        return {"count": 0, "results": []}

    from radar.etsy_api import EtsyPublicClient

    client = EtsyPublicClient("k:s", fetch=fake_fetch, min_interval=0)
    lane = Lane(id="x", keywords=["kw"], credibility=0.5, brand_fit="new_shop")

    sig = collect_lane_signals(client, lane, limit=5)

    assert sig.active_listings == 0
    assert sig.median_favorites == 0.0
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
    snaps = snapshot_own_listings(client, "YOUR_ETSY_SHOP_ID")

    assert snaps[0].views == 6
    assert snaps[0].price_usd == 19.0
    assert diagnose(snaps[0]) == "invisible"


def test_diagnose_seen_but_not_wanted():
    from radar.collectors import ListingSnapshot

    snap = ListingSnapshot(
        listing_id=2, title="T", views=250, favorites=0, price_usd=19.0
    )
    assert diagnose(snap) == "seen_not_wanted"
