from radar.config import Lane
from radar.models import Judgment, LaneSignals
from radar.scoring import (
    build_candidates,
    final_score,
    qualitative_score,
    route,
    verdict_for,
)

WEIGHTS = {
    "quantitative": {"demand": 0.40, "gap": 0.40, "price": 0.20},
    "qualitative": {
        "pain_urgency": 0.30,
        "willingness_to_pay": 0.30,
        "differentiation": 0.25,
        "credibility": 0.15,
    },
    "final": {"quantitative": 0.45, "qualitative": 0.35, "ease_to_create": 0.20},
}
THRESHOLDS = {"pursue": 0.65, "maybe": 0.40}

LANE = Lane(id="x", keywords=["kw"], credibility=1.0, brand_fit="careeros")


def _judgment(**over):
    base = dict(
        pain_urgency=1.0,
        willingness_to_pay=1.0,
        differentiation=1.0,
        ease_to_create=1.0,
        buildability="factory",
        buyer="b",
        product_format="f",
        differentiation_angle="d",
        why_this_could_sell="w",
        price_range_usd=[10, 20],
    )
    base.update(over)
    return Judgment(**base)


def test_qualitative_score_uses_lane_credibility_not_llm():
    low_cred_lane = Lane(id="y", keywords=["k"], credibility=0.0, brand_fit="new_shop")
    full = qualitative_score(_judgment(), LANE, WEIGHTS["qualitative"])
    reduced = qualitative_score(_judgment(), low_cred_lane, WEIGHTS["qualitative"])

    assert full == 1.0
    assert reduced == 0.85


def test_final_score_combines_all_three_terms():
    score = final_score(1.0, _judgment(), LANE, WEIGHTS)
    assert score == 1.0


def test_final_score_falls_back_to_quantitative_when_llm_unavailable():
    assert final_score(0.7, None, LANE, WEIGHTS) == 0.7


def test_verdict_thresholds():
    assert verdict_for(0.70, THRESHOLDS) == "pursue"
    assert verdict_for(0.65, THRESHOLDS) == "pursue"
    assert verdict_for(0.50, THRESHOLDS) == "maybe"
    assert verdict_for(0.20, THRESHOLDS) == "skip"


def test_routing_quadrants():
    assert route("careeros", "factory") == "auto_draft"
    assert route("careeros", "needs_new_capability") == "digest_idea"
    assert route("new_shop", "factory") == "new_shop_idea"
    assert route("new_shop", "needs_new_capability") == "digest_idea"


def test_build_candidates_sorts_by_score_descending():
    lanes = [
        Lane(id="weak", keywords=["a"], credibility=0.1, brand_fit="careeros"),
        Lane(id="strong", keywords=["b"], credibility=1.0, brand_fit="careeros"),
    ]
    signals = [
        LaneSignals("weak", "a", 10000, 5, 10.0, ["t"], 1),
        LaneSignals("strong", "b", 50, 200, 30.0, ["t"], 1),
    ]
    judgments = {"weak": _judgment(pain_urgency=0.1), "strong": _judgment()}

    cands = build_candidates(signals, judgments, lanes, WEIGHTS, THRESHOLDS)

    assert [c.lane_id for c in cands] == ["strong", "weak"]
    assert cands[0].score > cands[1].score
    assert cands[0].verdict in {"pursue", "maybe", "skip"}
