from radar.digest import render_digest
from radar.models import Candidate, ListingSnapshot


def _candidate(lane_id="x", verdict="pursue", score=0.8):
    return Candidate(
        niche="freelance client tracker",
        lane_id=lane_id,
        buyer="Solo consultants",
        product_format="Google Sheets + PDF",
        demand_signal={"median_favorites": 412, "sample_size": 20},
        competition_signal={"active_listings": 1840},
        gap_ratio=0.22,
        price_range_usd=[12, 29],
        ease_to_create=0.9,
        differentiation_angle="cash flow, not projects",
        why_this_could_sell="Strong favorites against thin competition.",
        brand_fit="careeros",
        buildability="factory",
        quantitative=0.7,
        qualitative=0.8,
        score=score,
        verdict=verdict,
    )


def test_digest_contains_all_sections():
    out = render_digest(
        run_date="2026-08-04",
        snapshots=[ListingSnapshot(4532224344, "AI Job Search", 6, 0, 19.0)],
        previous={4532224344: {"views": 2, "favorites": 0}},
        candidates=[_candidate()],
        llm_available=True,
    )

    assert "# Opportunity Radar — 2026-08-04" in out
    assert "## Existing listings" in out
    assert "## Ranked candidates" in out
    assert "## Top candidate" in out
    assert "invisible" in out
    assert "+4" in out  # views delta 6 - 2
    assert "freelance client tracker" in out
    assert "Strong favorites against thin competition." in out


def test_digest_warns_when_llm_unavailable():
    out = render_digest("2026-08-04", [], None, [_candidate()], llm_available=False)
    assert "quantitative-only" in out.lower()


def test_digest_handles_no_pursue_candidates():
    out = render_digest(
        "2026-08-04", [], None, [_candidate(verdict="skip", score=0.1)], True
    )
    assert "No candidate cleared the pursue threshold" in out


def test_digest_handles_no_candidates_at_all():
    out = render_digest("2026-08-04", [], None, [], True)
    assert "No candidates evaluated" in out


def test_digest_escapes_pipes_in_tables():
    """Regression: unescaped pipes in listing titles and candidate niches break tables."""
    candidate_with_pipe = Candidate(
        niche="tracker | spreadsheet tool",
        lane_id="x",
        buyer="Solo consultants",
        product_format="Google Sheets + PDF",
        demand_signal={"median_favorites": 412, "sample_size": 20},
        competition_signal={"active_listings": 1840},
        gap_ratio=0.22,
        price_range_usd=[12, 29],
        ease_to_create=0.9,
        differentiation_angle="cash flow, not projects",
        why_this_could_sell="Strong favorites against thin competition.",
        brand_fit="careeros",
        buildability="factory",
        quantitative=0.7,
        qualitative=0.8,
        score=0.8,
        verdict="pursue",
    )
    out = render_digest(
        run_date="2026-08-04",
        snapshots=[
            ListingSnapshot(
                4532224344,
                "AI Job Search | Google Sheets, Interview Prep (Digital Download)",
                6,
                0,
                19.0,
            )
        ],
        previous={4532224344: {"views": 2, "favorites": 0}},
        candidates=[candidate_with_pipe],
        llm_available=True,
    )

    # Pipes in listing title should be escaped
    assert "AI Job Search \\| Google Sheets" in out
    # Pipes in candidate niche should be escaped
    assert "tracker \\| spreadsheet tool" in out
    # The tables should have correct column counts (not broken by unescaped pipes)
    existing_lines = out.split("\n")
    existing_table_idx = next(i for i, line in enumerate(existing_lines) if "Existing listings" in line)
    # Find the header and data rows
    header_line = existing_lines[existing_table_idx + 2]
    assert header_line.count("|") == 7  # 6 columns = 7 pipes (including outer edges)
    data_line = existing_lines[existing_table_idx + 3]
    assert data_line.count("|") == 7  # Data row should have same count
