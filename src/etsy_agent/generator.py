from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "product"


@dataclass
class ProductInput:
    product_niche: str
    buyer: str
    product_format: str
    tone: str


def build_package(product_input: ProductInput) -> dict:
    niche = product_input.product_niche
    buyer = product_input.buyer
    product_format = product_input.product_format
    tone = product_input.tone

    title = "AI Job Search Command Center for Product Managers"
    tags = [
        "ai job search",
        "pm interview prep",
        "job search planner",
        "product manager",
        "career template",
        "google sheets",
        "interview tracker",
        "recruiter outreach",
        "behavioral stories",
        "carl framework",
        "career switch",
        "ai career tools",
        "digital download",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": asdict(product_input),
        "product_brief": {
            "niche": niche,
            "buyer": buyer,
            "format": product_format,
            "tone": tone,
            "positioning": (
                "A practical, operator-grade job-search system for product managers "
                "targeting AI-native roles."
            ),
            "jobs_to_be_done": [
                "Track active applications and interview loops in one place",
                "Capture recruiter outreach and follow-up messages quickly",
                "Maintain a reusable behavioral-story bank",
                "Run a weekly review without losing momentum",
            ],
        },
        "listing": {
            "title": title,
            "price_recommendation_usd": 24,
            "tags": tags,
            "description": (
                "A premium digital toolkit for product managers running a structured AI-era job search. "
                "Includes a job tracker, interview prep worksheet, recruiter outreach templates, "
                "CARL story bank worksheet, and weekly review planner.\n\n"
                "AI disclosure: AI tools were used to help draft and structure portions of the content. "
                "Final product design, review, and packaging were completed by the seller."
            ),
        },
        "deliverables": {
            "file_manifest": [
                "job-tracker-template.xlsx or Google Sheets equivalent",
                "interview-prep-worksheet.pdf",
                "recruiter-outreach-templates.pdf",
                "carl-story-bank-worksheet.pdf",
                "weekly-review-planner.pdf",
                "buyer-instructions.pdf",
            ],
            "listing_image_prompts": [
                "Clean premium Etsy hero image showing AI Job Search Command Center for Product Managers with spreadsheet and worksheet previews",
                "Feature image focused on recruiter outreach templates and CARL story bank pages",
                "Workflow image showing weekly review cadence and interview prep system",
            ],
        },
        "github_demo_notes": [
            "This output is draft-only and requires manual review before listing publication.",
            "Next implementation step: wire model generation and Etsy draft-listing API flow.",
        ],
    }


def write_package(base_dir: Path, product_input: ProductInput) -> Path:
    payload = build_package(product_input)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = base_dir / "outputs" / f"{timestamp}-{_slugify(product_input.product_niche)}"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "package.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Draft Listing Package\n\n"
        f"- Product niche: {product_input.product_niche}\n"
        f"- Buyer: {product_input.buyer}\n"
        f"- Format: {product_input.product_format}\n"
        f"- Tone: {product_input.tone}\n",
        encoding="utf-8",
    )
    return output_dir
