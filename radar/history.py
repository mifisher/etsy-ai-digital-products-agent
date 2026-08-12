from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from radar.models import Candidate, ListingSnapshot

logger = logging.getLogger(__name__)


def _snapshot_dir(root: Path) -> Path:
    path = root / "snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_snapshot(
    root: Path, run_date: str, snapshots: list[ListingSnapshot]
) -> Path:
    target = _snapshot_dir(root) / f"{run_date}.json"
    payload = {str(s.listing_id): asdict(s) for s in snapshots}
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_previous_snapshot(root: Path, before: str) -> dict[int, dict] | None:
    directory = root / "snapshots"
    if not directory.exists():
        return None
    earlier = sorted(p for p in directory.glob("*.json") if p.stem < before)
    if not earlier:
        return None
    data = json.loads(earlier[-1].read_text(encoding="utf-8"))
    return {int(k): v for k, v in data.items()}


def append_decisions(
    root: Path, run_date: str, candidates: list[Candidate]
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    log = root / "decisions.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(
                json.dumps(
                    {
                        "date": run_date,
                        "lane_id": candidate.lane_id,
                        "niche": candidate.niche,
                        "score": round(candidate.score, 4),
                        "verdict": candidate.verdict,
                    }
                )
                + "\n"
            )


def recently_rejected(root: Path, run_date: str, cooldown_days: int) -> set[str]:
    """Lane ids skipped recently, so the radar stops re-proposing dead ends."""
    log = root / "decisions.jsonl"
    if not log.exists():
        return set()

    cutoff = date.fromisoformat(run_date) - timedelta(days=cooldown_days)
    rejected: set[str] = set()
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if record.get("verdict") != "skip":
                continue
            if date.fromisoformat(record["date"]) >= cutoff:
                rejected.add(record["lane_id"])
        except Exception as exc:
            logger.warning(
                "Skipping malformed decisions.jsonl line: %s", exc
            )
            continue
    return rejected
