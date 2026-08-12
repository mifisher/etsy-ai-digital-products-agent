from __future__ import annotations

import statistics

from radar.config import Lane
from radar.etsy_api import EtsyPublicClient
from radar.models import LaneSignals, ListingSnapshot

# A listing with real exposure but no favorites is a conversion problem,
# not a visibility problem. Below this view count we cannot tell yet.
VISIBILITY_VIEW_FLOOR = 100


def _price_usd(listing: dict) -> float:
    price = listing.get("price") or {}
    amount = price.get("amount", 0)
    divisor = price.get("divisor", 100) or 100
    return amount / divisor


def collect_lane_signals(
    client: EtsyPublicClient, lane: Lane, limit: int
) -> LaneSignals:
    keyword = lane.keywords[0]
    data = client.search_active(keyword, limit=limit)
    results = data.get("results", [])

    favorites = [r.get("num_favorers", 0) or 0 for r in results]
    prices = [_price_usd(r) for r in results]

    return LaneSignals(
        lane_id=lane.id,
        keyword=keyword,
        active_listings=data.get("count", 0) or 0,
        mean_favorites=statistics.fmean(favorites) if favorites else 0.0,
        median_price=statistics.median(prices) if prices else 0.0,
        sample_titles=[r.get("title", "") for r in results],
        sample_size=len(results),
    )


def snapshot_own_listings(
    client: EtsyPublicClient, shop_id: str
) -> list[ListingSnapshot]:
    return [
        ListingSnapshot(
            listing_id=r.get("listing_id", 0),
            title=r.get("title", ""),
            views=r.get("views", 0) or 0,
            favorites=r.get("num_favorers", 0) or 0,
            price_usd=_price_usd(r),
        )
        for r in client.shop_active_listings(shop_id)
    ]


def diagnose(snapshot: ListingSnapshot) -> str:
    """Classify why a listing is not selling."""
    if snapshot.views < VISIBILITY_VIEW_FLOOR:
        return "invisible"
    if snapshot.favorites == 0:
        return "seen_not_wanted"
    return "converting"
