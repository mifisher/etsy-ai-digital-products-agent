import pytest

from radar.models import LaneSignals
from radar.scoring import gap_ratios, log_minmax, quantitative_scores

QUANT_WEIGHTS = {"demand": 0.40, "gap": 0.40, "price": 0.20}


def _sig(lane_id, favs, listings, price):
    return LaneSignals(
        lane_id=lane_id,
        keyword="k",
        active_listings=listings,
        mean_favorites=favs,
        median_price=price,
        sample_size=20,
    )


def test_log_minmax_spans_zero_to_one():
    out = log_minmax([1.0, 10.0, 100.0])
    assert out[0] == pytest.approx(0.0)
    assert out[-1] == pytest.approx(1.0)
    assert 0.0 < out[1] < 1.0


def test_log_minmax_identical_values_returns_neutral():
    assert log_minmax([5.0, 5.0, 5.0]) == [0.5, 0.5, 0.5]


def test_log_minmax_single_value_returns_neutral():
    assert log_minmax([7.0]) == [0.5]


def test_log_minmax_handles_zeros():
    out = log_minmax([0.0, 0.0, 50.0])
    assert out[0] == pytest.approx(0.0)
    assert out[-1] == pytest.approx(1.0)


def test_gap_ratio_rewards_underserved_niches():
    crowded = _sig("crowded", favs=100, listings=10000, price=15)
    underserved = _sig("underserved", favs=100, listings=50, price=15)

    ratios = gap_ratios([crowded, underserved])

    assert ratios[1] > ratios[0]


def test_gap_ratio_never_divides_by_zero():
    empty = _sig("empty", favs=10, listings=0, price=15)
    assert gap_ratios([empty])[0] == 10.0


def test_quantitative_score_ranks_underserved_above_crowded():
    crowded = _sig("crowded", favs=100, listings=10000, price=15)
    underserved = _sig("underserved", favs=100, listings=50, price=15)

    scores = quantitative_scores([crowded, underserved], QUANT_WEIGHTS)

    assert scores[1] > scores[0]
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_quantitative_score_empty_input():
    assert quantitative_scores([], QUANT_WEIGHTS) == []
