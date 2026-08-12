from pathlib import Path

import pytest

from radar.config import load_config


def test_loads_lanes_and_weights(tmp_path: Path):
    cfg_file = tmp_path / "lanes.yml"
    cfg_file.write_text(
        "shop_id: '123'\n"
        "lanes:\n"
        "  - id: a\n"
        "    keywords: ['k1', 'k2']\n"
        "    credibility: 0.9\n"
        "    brand_fit: careeros\n"
        "weights:\n"
        "  quantitative: {demand: 0.4, gap: 0.4, price: 0.2}\n"
        "  qualitative: {pain_urgency: 0.3, willingness_to_pay: 0.3,"
        " differentiation: 0.25, credibility: 0.15}\n"
        "  final: {quantitative: 0.45, qualitative: 0.35, ease_to_create: 0.2}\n"
        "thresholds: {pursue: 0.65, maybe: 0.4}\n"
        "limits: {search_limit: 20, reject_cooldown_days: 30}\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)

    assert cfg.shop_id == "123"
    assert len(cfg.lanes) == 1
    assert cfg.lanes[0].keywords == ["k1", "k2"]
    assert cfg.lanes[0].credibility == 0.9
    assert cfg.weights["final"]["quantitative"] == 0.45
    assert cfg.thresholds["pursue"] == 0.65
    assert cfg.limits["search_limit"] == 20


def _write_config(tmp_path: Path, quantitative_weights: str) -> Path:
    cfg_file = tmp_path / "lanes.yml"
    cfg_file.write_text(
        "shop_id: '123'\n"
        "lanes:\n"
        "  - id: a\n"
        "    keywords: ['k1', 'k2']\n"
        "    credibility: 0.9\n"
        "    brand_fit: careeros\n"
        "weights:\n"
        f"  quantitative: {quantitative_weights}\n"
        "  qualitative: {pain_urgency: 0.3, willingness_to_pay: 0.3,"
        " differentiation: 0.25, credibility: 0.15}\n"
        "  final: {quantitative: 0.45, qualitative: 0.35, ease_to_create: 0.2}\n"
        "thresholds: {pursue: 0.65, maybe: 0.4}\n"
        "limits: {search_limit: 20, reject_cooldown_days: 30}\n",
        encoding="utf-8",
    )
    return cfg_file


def test_rejects_weight_group_that_does_not_sum_to_one(tmp_path: Path):
    cfg_file = _write_config(tmp_path, "{demand: 0.40, gap: 0.40, price: 0.30}")

    with pytest.raises(ValueError) as excinfo:
        load_config(cfg_file)

    message = str(excinfo.value)
    assert "quantitative" in message
    assert "1.1" in message or "1.1000000000000" in message


def test_accepts_weight_group_within_floating_point_tolerance(tmp_path: Path):
    # 0.1 + 0.2 + 0.7 != 1.0 exactly in binary floating point; this must
    # still be accepted since it's within the tolerance band.
    cfg_file = _write_config(tmp_path, "{demand: 0.1, gap: 0.2, price: 0.7}")

    cfg = load_config(cfg_file)

    assert cfg.weights["quantitative"]["demand"] == 0.1
