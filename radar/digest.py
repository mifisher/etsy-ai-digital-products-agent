from __future__ import annotations

from radar.collectors import diagnose
from radar.models import Candidate, ListingSnapshot

PRESCRIPTION = {
    "invisible": "Rewrite title and tags for search — nobody is seeing this.",
    "seen_not_wanted": "Revisit price, images, and positioning — seen but not saved.",
    "converting": "Working. Leave it alone.",
}


def _esc(text: str) -> str:
    """Escape pipes so free text cannot break a markdown table row."""
    return str(text).replace("|", "\\|")


def _delta(current: int, previous: dict | None, key: str) -> str:
    if not previous:
        return "n/a"
    change = current - previous.get(key, 0)
    return f"+{change}" if change >= 0 else str(change)


def render_digest(
    run_date: str,
    snapshots: list[ListingSnapshot],
    previous: dict[int, dict] | None,
    candidates: list[Candidate],
    llm_available: bool,
    judged_count: int | None = None,
    total_count: int | None = None,
) -> str:
    lines = [f"# Opportunity Radar — {run_date}", ""]

    top = next((c for c in candidates if c.verdict == "pursue"), None)
    if not candidates:
        lines += ["**No candidates evaluated this run.**", ""]
    elif top:
        lines += [f"**This week: build `{top.niche}`** (score {top.score:.2f}).", ""]
    else:
        lines += [
            "**No candidate cleared the pursue threshold.** "
            "Focus on the existing listing instead.",
            "",
        ]

    if not llm_available:
        if judged_count is not None and total_count is not None:
            lines += [
                f"> ⚠️ LLM judgment incomplete this run "
                f"({judged_count}/{total_count} lanes judged) — ranking is "
                "**quantitative-only**. Treat verdicts as provisional.",
                "",
            ]
        else:
            lines += [
                "> ⚠️ LLM judgment unavailable this run — ranking is "
                "**quantitative-only**. Treat verdicts as provisional.",
                "",
            ]

    lines += ["## Existing listings", ""]
    if not snapshots:
        lines += ["_No active listings._", ""]
    else:
        lines += [
            "| Listing | Views | Δ | Favorites | Diagnosis | Prescription |",
            "|---|---|---|---|---|---|",
        ]
        for snap in snapshots:
            prev = (previous or {}).get(snap.listing_id)
            state = diagnose(snap)
            lines.append(
                f"| {_esc(snap.title[:40])} | {snap.views} | "
                f"{_delta(snap.views, prev, 'views')} | {snap.favorites} | "
                f"{state} | {PRESCRIPTION[state]} |"
            )
        lines.append("")

    lines += ["## Ranked candidates", ""]
    if candidates:
        lines += [
            "| Niche | Score | Verdict | Mean Favorites | Competing | Gap |",
            "|---|---|---|---|---|---|",
        ]
        for c in candidates:
            lines.append(
                f"| {_esc(c.niche)} | {c.score:.2f} | {c.verdict} | "
                f"{c.demand_signal.get('mean_favorites', 0)} | "
                f"{c.competition_signal.get('active_listings', 0)} | "
                f"{c.gap_ratio:.3f} |"
            )
        lines.append("")

    if top:
        lines += [
            "## Top candidate",
            "",
            f"**{top.niche}** — {top.product_format}",
            "",
            f"- **Buyer:** {top.buyer}",
            f"- **Price range:** ${top.price_range_usd[0]}–${top.price_range_usd[1]}"
            if len(top.price_range_usd) == 2
            else "- **Price range:** n/a",
            f"- **Angle:** {top.differentiation_angle}",
            f"- **Routing:** {top.brand_fit} / {top.buildability}",
            "",
            f"{top.why_this_could_sell}",
            "",
        ]

    ideas = [c for c in candidates if c.brand_fit == "new_shop" and c.verdict != "skip"]
    if ideas:
        lines += ["## New-shop ideas", ""]
        lines += [f"- **{c.niche}** ({c.score:.2f}) — {c.differentiation_angle}" for c in ideas]
        lines.append("")

    return "\n".join(lines)
