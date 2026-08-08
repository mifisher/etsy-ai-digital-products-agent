from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Lane:
    id: str
    keywords: list[str]
    credibility: float
    brand_fit: str


@dataclass
class Config:
    shop_id: str
    lanes: list[Lane]
    weights: dict
    thresholds: dict
    limits: dict


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    lanes = [
        Lane(
            id=item["id"],
            keywords=list(item["keywords"]),
            credibility=float(item["credibility"]),
            brand_fit=item["brand_fit"],
        )
        for item in data["lanes"]
    ]
    return Config(
        shop_id=str(data["shop_id"]),
        lanes=lanes,
        weights=data["weights"],
        thresholds=data["thresholds"],
        limits=data["limits"],
    )
