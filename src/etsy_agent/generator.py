from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
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


def _generate_tags(niche: str, product_format: str, tone: str) -> list[str]:
    niche_words = [w for w in _slugify(niche).split("-") if len(w) > 2]
    format_words = [w for w in _slugify(product_format).split("-") if len(w) > 2]
    tone_words = [w for w in _slugify(tone).split("-") if len(w) > 2]

    base_tags = [
        "digital download",
        "printable",
        "instant download",
        "template",
    ]
    if "sheet" in product_format.lower() or "excel" in product_format.lower() or "csv" in product_format.lower():
        base_tags += ["spreadsheet", "google sheets", "excel template"]
    if "pdf" in product_format.lower():
        base_tags += ["pdf", "printable planner"]
    if "notion" in product_format.lower():
        base_tags += ["notion template", "notion dashboard"]
    if "ai" in niche.lower():
        base_tags += ["ai tools", "ai powered"]

    dynamic = niche_words[:6] + format_words[:3] + tone_words[:2]
    dynamic = [w.replace("-", " ") for w in dynamic]

    tags = list(dict.fromkeys([t.lower().strip() for t in dynamic + base_tags]))
    return tags[:13]


def _generate_title(niche: str, product_format: str, tone: str) -> str:
    tone_prefix = ""
    if "premium" in tone.lower() or "luxury" in tone.lower():
        tone_prefix = "Premium "
    elif "simple" in tone.lower() or "minimal" in tone.lower():
        tone_prefix = "Minimal "
    elif "pro" in tone.lower() or "operator" in tone.lower():
        tone_prefix = "Pro "

    fmt = product_format.split("+")[0].strip()
    short_niche = niche[:50] if len(niche) > 50 else niche
    title = f"{tone_prefix}{short_niche.title()} | {fmt.title()} Template"
    if len(title) > 140:
        title = title[:137] + "..."
    return title


def _generate_brief(niche: str, buyer: str, product_format: str, tone: str) -> dict:
    tone_adj = tone.split(",")[0].strip().lower()
    jobs = [
        f"Organize and streamline their {niche} workflow",
        f"Save hours on manual {product_format.split('+')[0].strip()} setup",
        f"Get started immediately with a proven, {tone_adj} system",
    ]
    return {
        "niche": niche,
        "buyer": buyer,
        "format": product_format,
        "tone": tone,
        "positioning": (
            f"A {tone_adj} digital toolkit for {buyer} who want a ready-to-use "
            f"{product_format} system for {niche}."
        ),
        "jobs_to_be_done": jobs,
    }


def _generate_deliverables(niche: str, product_format: str) -> dict:
    fmts = [f.strip() for f in product_format.split("+")]
    manifest = []
    for i, fmt in enumerate(fmts, 1):
        ext = "pdf"
        if "sheet" in fmt.lower() or "excel" in fmt.lower():
            ext = "xlsx"
        if "notion" in fmt.lower():
            ext = "notion"
        manifest.append(f"{i:02d}-{_slugify(niche)}-{_slugify(fmt)}.{ext}")
    manifest.append("buyer-setup-guide.pdf")

    image_prompts = [
        f"Clean premium Etsy hero image showing {niche} {product_format} template with mockup preview",
        f"Feature image focused on key worksheets and layouts from the {niche} toolkit",
        f"Lifestyle image showing a professional using the {product_format} system on a laptop",
    ]
    return {"file_manifest": manifest, "listing_image_prompts": image_prompts}


def _generate_description(product_input: ProductInput) -> str:
    pi = product_input
    return (
        f"A {pi.tone.split(',')[0].strip().lower()} digital toolkit for {pi.buyer} "
        f"who want a ready-to-use {pi.product_format} system for {pi.product_niche}.\n\n"
        "What's included:\n"
        + "\n".join(f"• {f}" for f in _generate_deliverables(pi.product_niche, pi.product_format)["file_manifest"])
        + "\n\n"
        "How it helps:\n"
        "• Save hours of setup time\n"
        "• Get organized fast with a proven structure\n"
        "• Start seeing results immediately after purchase\n\n"
        "AI disclosure: AI tools were used to help draft and structure portions of the content. "
        "Final product design, review, and packaging were completed by the seller."
    )


def _llm_generate_package(product_input: ProductInput) -> dict:
    try:
        import openai
    except ModuleNotFoundError:
        raise RuntimeError(
            "openai package is not installed. Install it (e.g. pip install openai) "
            "or unset ETSY_USE_LLM to use deterministic generation."
        )

    client = openai.OpenAI()
    system_prompt = (
        "You are an expert Etsy listing copywriter and digital-product strategist. "
        "Given a product niche, buyer persona, format, and tone, output ONLY a valid JSON object with:\n"
        "- title: catchy Etsy title (max 140 chars)\n"
        "- price_recommendation_usd: integer price point\n"
        "- tags: list of up to 13 Etsy search tags\n"
        "- description: compelling listing description with AI disclosure\n"
        "- positioning: one-sentence value prop\n"
        "- jobs_to_be_done: list of 3 buyer outcomes\n"
        "- file_manifest: list of deliverable filenames\n"
        "- listing_image_prompts: list of 3 image-generation prompts"
    )
    user_prompt = (
        f"Niche: {product_input.product_niche}\n"
        f"Buyer: {product_input.buyer}\n"
        f"Format: {product_input.product_format}\n"
        f"Tone: {product_input.tone}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except openai.RateLimitError as exc:
        raise RuntimeError(
            "OpenAI rate limit or quota exceeded. "
            "Unset ETSY_USE_LLM to fall back to deterministic generation."
        ) from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content")
    data = json.loads(content)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": asdict(product_input),
        "product_brief": {
            "niche": product_input.product_niche,
            "buyer": product_input.buyer,
            "format": product_input.product_format,
            "tone": product_input.tone,
            "positioning": data.get("positioning", ""),
            "jobs_to_be_done": data.get("jobs_to_be_done", []),
        },
        "listing": {
            "title": data.get("title", ""),
            "price_recommendation_usd": data.get("price_recommendation_usd", 19),
            "tags": data.get("tags", []),
            "description": data.get("description", ""),
        },
        "deliverables": {
            "file_manifest": data.get("file_manifest", []),
            "listing_image_prompts": data.get("listing_image_prompts", []),
        },
        "github_demo_notes": [
            "LLM-generated draft. Review before publishing.",
        ],
    }


def build_package(product_input: ProductInput) -> dict:
    if os.getenv("ETSY_USE_LLM", "").lower() in ("1", "true", "yes"):
        return _llm_generate_package(product_input)

    brief = _generate_brief(
        product_input.product_niche,
        product_input.buyer,
        product_input.product_format,
        product_input.tone,
    )
    deliverables = _generate_deliverables(
        product_input.product_niche, product_input.product_format
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": asdict(product_input),
        "product_brief": brief,
        "listing": {
            "title": _generate_title(
                product_input.product_niche, product_input.product_format, product_input.tone
            ),
            "price_recommendation_usd": 19,
            "tags": _generate_tags(
                product_input.product_niche, product_input.product_format, product_input.tone
            ),
            "description": _generate_description(product_input),
        },
        "deliverables": deliverables,
        "github_demo_notes": [
            "This output is draft-only and requires manual review before listing publication.",
            "Set ETSY_USE_LLM=1 to enable LLM-backed generation.",
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
