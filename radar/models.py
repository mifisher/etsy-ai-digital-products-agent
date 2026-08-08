from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LaneSignals:
    lane_id: str
    keyword: str
    active_listings: int
    median_favorites: float
    median_price: float
    sample_titles: list[str] = field(default_factory=list)
    sample_size: int = 0


@dataclass
class ListingSnapshot:
    listing_id: int
    title: str
    views: int
    favorites: int
    price_usd: float


@dataclass
class Judgment:
    pain_urgency: float
    willingness_to_pay: float
    differentiation: float
    ease_to_create: float
    buildability: str
    buyer: str
    product_format: str
    differentiation_angle: str
    why_this_could_sell: str
    price_range_usd: list[int]


@dataclass
class Candidate:
    niche: str
    lane_id: str
    buyer: str
    product_format: str
    demand_signal: dict
    competition_signal: dict
    gap_ratio: float
    price_range_usd: list[int]
    ease_to_create: float
    differentiation_angle: str
    why_this_could_sell: str
    brand_fit: str
    buildability: str
    quantitative: float
    qualitative: float | None
    score: float
    verdict: str
