from __future__ import annotations

import argparse
import logging
import os
from datetime import date
from pathlib import Path
from typing import Callable

from radar.collectors import collect_lane_signals, snapshot_own_listings
from radar.config import Config, Lane, load_config
from radar.digest import render_digest
from radar.etsy_api import EtsyPublicClient
from radar.history import (
    append_decisions,
    load_previous_snapshot,
    recently_rejected,
    write_snapshot,
)
from radar.models import Judgment, LaneSignals
from radar.scoring import build_candidates

logger = logging.getLogger(__name__)


def run_radar(
    config: Config,
    client: EtsyPublicClient,
    run_date: str,
    history_root: Path,
    judge: Callable[[Lane, LaneSignals], Judgment | None],
    dry_run: bool = False,
) -> tuple[str, Path | None]:
    skip = recently_rejected(
        history_root, run_date, config.limits["reject_cooldown_days"]
    )

    # Collect and score every lane so log_minmax normalizes within the full
    # pool. The cooldown is applied as a filter on the results below, right
    # before the digest is rendered and decisions are appended — not before
    # collection/scoring — otherwise a near-total cooldown collapses the
    # normalization pool to one lane and degenerates every score to 0.5.
    lanes = config.lanes

    signals = [
        collect_lane_signals(client, lane, config.limits["search_limit"])
        for lane in lanes
    ]
    judgments = {lane.id: judge(lane, sig) for lane, sig in zip(lanes, signals)}

    candidates = build_candidates(
        signals, judgments, lanes, config.weights, config.thresholds
    )

    # Only lanes not currently in cooldown are visible in the digest and may
    # have a new decision recorded. Re-appending a "skip" for a cooled lane
    # every week would push its cutoff date forward forever, so a suppressed
    # lane must never get a fresh decision written for it.
    visible_candidates = [c for c in candidates if c.lane_id not in skip]

    # Scope the "how many were judged" banner to what the digest actually
    # displays. A lane suppressed by the cooldown isn't in the table, so its
    # judgment outcome shouldn't trigger (or silence) a warning about rows
    # the reader can actually see. `qualitative` is None exactly when a
    # candidate's judgment was unavailable (see build_candidates).
    judged_count = sum(1 for c in visible_candidates if c.qualitative is not None)
    total_count = len(visible_candidates)
    llm_available = judged_count == total_count

    snapshots = snapshot_own_listings(client, config.shop_id)
    previous = load_previous_snapshot(history_root, before=run_date)

    markdown = render_digest(
        run_date,
        snapshots,
        previous,
        visible_candidates,
        llm_available,
        judged_count=judged_count,
        total_count=total_count,
    )

    if dry_run:
        return markdown, None

    write_snapshot(history_root, run_date, snapshots)
    append_decisions(history_root, run_date, visible_candidates)
    digests = history_root / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    path = digests / f"{run_date}.md"
    path.write_text(markdown, encoding="utf-8")
    return markdown, path


def _build_judge():
    """Return a judge callable, degrading to no-op if the LLM is unusable."""
    try:
        from radar.llm import build_client, judge_lane

        client, model = build_client()
    except Exception as exc:
        logger.warning(
            "LLM client unavailable, falling back to quantitative-only "
            "scoring: %s",
            exc,
        )
        return lambda lane, signals: None
    return lambda lane, signals: judge_lane(client, model, lane, signals)


def main() -> None:
    parser = argparse.ArgumentParser(description="Etsy Opportunity Radar")
    parser.add_argument("--config", default="config/lanes.yml")
    parser.add_argument("--history", default="history")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = (
        f"{os.environ['ETSY_CLIENT_ID']}:{os.environ['ETSY_CLIENT_SECRET']}"
    )
    config = load_config(args.config)
    client = EtsyPublicClient(api_key)

    markdown, path = run_radar(
        config,
        client,
        args.date,
        Path(args.history),
        judge=_build_judge(),
        dry_run=args.dry_run,
    )
    print(markdown)
    if path:
        print(f"\nWritten to {path}")


if __name__ == "__main__":
    main()
