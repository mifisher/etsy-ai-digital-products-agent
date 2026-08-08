from __future__ import annotations

import math

from radar.config import Lane
from radar.models import Candidate, Judgment, LaneSignals


def log_minmax(values: list[float]) -> list[float]:
    """Log-scale then min-max normalize within the candidate pool.

    Favorite and listing counts are heavy-tailed, so raw min-max would let a
    single viral listing flatten everything else. Scores are comparative
    within one run, not absolute across runs.
    """
    if not values:
        return []
    logs = [math.log1p(max(v, 0.0)) for v in values]
    lo, hi = min(logs), max(logs)
    if hi - lo < 1e-9:
        return [0.5] * len(logs)
    return [(x - lo) / (hi - lo) for x in logs]


def gap_ratios(signals: list[LaneSignals]) -> list[float]:
    """Demand per unit of competition — the underserved-ness term."""
    return [s.median_favorites / max(s.active_listings, 1) for s in signals]


def quantitative_scores(signals: list[LaneSignals], weights: dict) -> list[float]:
    if not signals:
        return []
    demand = log_minmax([s.median_favorites for s in signals])
    gap = log_minmax(gap_ratios(signals))
    price = log_minmax([s.median_price for s in signals])
    return [
        weights["demand"] * d + weights["gap"] * g + weights["price"] * p
        for d, g, p in zip(demand, gap, price)
    ]


def qualitative_score(judgment: Judgment, lane: Lane, weights: dict) -> float:
    """Credibility comes from lane config, not the LLM.

    Asking a model to rate the seller's own credibility invites flattery;
    the human-set per-lane value is the honest signal.
    """
    return (
        weights["pain_urgency"] * judgment.pain_urgency
        + weights["willingness_to_pay"] * judgment.willingness_to_pay
        + weights["differentiation"] * judgment.differentiation
        + weights["credibility"] * lane.credibility
    )


def final_score(
    quant: float, judgment: Judgment | None, lane: Lane, weights: dict
) -> float:
    if judgment is None:
        return quant
    qual = qualitative_score(judgment, lane, weights["qualitative"])
    final = weights["final"]
    return (
        final["quantitative"] * quant
        + final["qualitative"] * qual
        + final["ease_to_create"] * judgment.ease_to_create
    )


def verdict_for(score: float, thresholds: dict) -> str:
    if score >= thresholds["pursue"]:
        return "pursue"
    if score >= thresholds["maybe"]:
        return "maybe"
    return "skip"


def route(brand_fit: str, buildability: str) -> str:
    if buildability != "factory":
        return "digest_idea"
    return "auto_draft" if brand_fit == "careeros" else "new_shop_idea"


def build_candidates(
    signals: list[LaneSignals],
    judgments: dict[str, Judgment | None],
    lanes: list[Lane],
    weights: dict,
    thresholds: dict,
) -> list[Candidate]:
    lanes_by_id = {lane.id: lane for lane in lanes}
    quants = quantitative_scores(signals, weights["quantitative"])
    gaps = gap_ratios(signals)

    candidates = []
    for sig, quant, gap in zip(signals, quants, gaps):
        lane = lanes_by_id[sig.lane_id]
        judgment = judgments.get(sig.lane_id)
        score = final_score(quant, judgment, lane, weights)
        candidates.append(
            Candidate(
                niche=sig.keyword,
                lane_id=sig.lane_id,
                buyer=judgment.buyer if judgment else "",
                product_format=judgment.product_format if judgment else "",
                demand_signal={
                    "median_favorites": sig.median_favorites,
                    "sample_size": sig.sample_size,
                },
                competition_signal={"active_listings": sig.active_listings},
                gap_ratio=gap,
                price_range_usd=judgment.price_range_usd if judgment else [],
                ease_to_create=judgment.ease_to_create if judgment else 0.0,
                differentiation_angle=(
                    judgment.differentiation_angle if judgment else ""
                ),
                why_this_could_sell=(
                    judgment.why_this_could_sell
                    if judgment
                    else "Quantitative signals only — LLM judgment unavailable."
                ),
                brand_fit=lane.brand_fit,
                buildability=(
                    judgment.buildability if judgment else "needs_new_capability"
                ),
                quantitative=quant,
                qualitative=(
                    qualitative_score(judgment, lane, weights["qualitative"])
                    if judgment
                    else None
                ),
                score=score,
                verdict=verdict_for(score, thresholds),
            )
        )

    return sorted(candidates, key=lambda c: c.score, reverse=True)
