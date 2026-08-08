from pathlib import Path
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
