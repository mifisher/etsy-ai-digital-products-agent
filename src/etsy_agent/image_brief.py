from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json


@dataclass
class ImagePrompt:
    name: str
    purpose: str
    ratio: str
    dimensions: str
    prompt: str
    tips: list[str]


@dataclass
class ImageBrief:
    generated_at: str
    niche: str
    format_str: str
    tone: str
    images: list[ImagePrompt]
    etsy_guidelines: dict


ETSY_GUIDELINES = {
    "min_size": "2000 x 2000 pixels",
    "recommended_ratio": "1:1 (square) for main image, 4:3 for secondary",
    "max_images": 10,
    "file_formats": ["JPEG", "PNG"],
    "tips": [
        "First image is the thumbnail — make it pop at small sizes",
        "Show the product in use or context, not just flat lay",
        "Include text overlays for key benefits (readable at 200px wide)",
        "Use consistent color palette across all images",
        "Add a size/reference object so buyers understand scale",
    ],
}


def _hero_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    return ImagePrompt(
        name="Hero Image",
        purpose="Main thumbnail — first impression, must stop the scroll",
        ratio="1:1",
        dimensions="2000 x 2000 px",
        prompt=(
            f"Premium Etsy listing hero image for a {tone_adj} digital product: "
            f"'{niche}' in {format_str} format. "
            f"Clean modern layout with subtle gradient background, "
            f"product mockup on a laptop/tablet screen, "
            f"bold readable title text overlay, "
            f"minimalist icons representing key features, "
            f"soft shadows, professional product photography style, "
            f"high contrast, eye-catching at small thumbnail size"
        ),
        tips=[
            "Use large, readable text — 50% of buyers are on mobile",
            "Show the device/mockup at an angle for depth",
            "Keep background simple — solid color or subtle texture",
        ],
    )


def _feature_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    fmts = [f.strip() for f in format_str.split("+")]
    return ImagePrompt(
        name="Feature Breakdown",
        purpose="Show what's included — pages, templates, dashboards",
        ratio="4:3",
        dimensions="2000 x 1500 px",
        prompt=(
            f"Clean feature showcase image for '{niche}' digital product. "
            f"Display {len(fmts)} preview panels side by side showing "
            f"{', '.join(fmts)} layouts. "
            f"Each panel has a subtle drop shadow, labeled with clean typography. "
            f"{tone_adj} aesthetic, organized grid layout, "
            f"soft neutral background, professional digital product preview"
        ),
        tips=[
            "Label each section clearly (e.g., 'Dashboard', 'Tracker', 'Templates')",
            "Use real-looking content, not lorem ipsum",
            "Zoom in enough that text is readable but not cluttered",
        ],
    )


def _lifestyle_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    return ImagePrompt(
        name="Lifestyle / In-Use",
        purpose="Help buyer imagine themselves using the product",
        ratio="4:3",
        dimensions="2000 x 1500 px",
        prompt=(
            f"Lifestyle photograph showing a professional using a {format_str} "
            f"'{niche}' system on a laptop at a clean modern desk. "
            f"{tone_adj} workspace aesthetic, natural lighting, "
            f"coffee cup and notebook nearby, shallow depth of field, "
            f"screen content slightly blurred but recognizable, "
            f"warm inviting atmosphere, aspirational but achievable"
        ),
        tips=[
            "Show a diverse, relatable person (or hands-only if avoiding faces)",
            "Natural light looks more authentic than studio flash",
            "Include 1-2 context props (coffee, plant, notebook) but don't clutter",
        ],
    )


def _detail_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    return ImagePrompt(
        name="Detail / Close-Up",
        purpose="Show quality and attention to detail",
        ratio="1:1",
        dimensions="2000 x 2000 px",
        prompt=(
            f"Close-up detail shot of a {tone_adj} '{niche}' template page. "
            f"Focus on clean typography, structured layout, and color-coded sections. "
            f"Macro-style digital product photography, crisp text edges, "
            f"subtle grid lines, professional formatting visible, "
            f"soft bokeh background, premium feel"
        ),
        tips=[
            "Zoom in on the most visually appealing section",
            "Show color palette consistency",
            "Highlight any unique design elements (icons, charts, progress bars)",
        ],
    )


def _comparison_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    return ImagePrompt(
        name="Before / After or Comparison",
        purpose="Show the transformation your product provides",
        ratio="4:3",
        dimensions="2000 x 1500 px",
        prompt=(
            f"Split-screen comparison image: left side shows messy, disorganized "
            f"{format_str} notes/scribbles for '{niche}'; "
            f"right side shows the same content transformed with the {tone_adj} "
            f"template — clean, structured, color-coded, organized. "
            f"Visual storytelling, dramatic contrast, "
            f"arrow or divider between sides, professional layout"
        ),
        tips=[
            "Make the 'before' relatable but not ugly — buyers resist feeling judged",
            "The 'after' should look achievable, not overly polished",
            "Add a subtle 'After using [Product Name]' label",
        ],
    )


def _social_proof_prompt(niche: str, format_str: str, tone: str) -> ImagePrompt:
    tone_adj = tone.split(",")[0].strip().lower()
    return ImagePrompt(
        name="Social Proof / Results",
        purpose="Build trust with testimonials or result previews",
        ratio="4:3",
        dimensions="2000 x 1500 px",
        prompt=(
            f"Testimonial-style image for '{niche}' digital product. "
            f"Elegant quote card design with 5-star rating, "
            f"clean sans-serif typography, {tone_adj} color palette, "
            f"subtle gradient background, small product thumbnail in corner, "
            f"professional review card aesthetic, trustworthy and inviting"
        ),
        tips=[
            "Use real quotes from beta testers if available",
            "If no testimonials yet, show 'results' (e.g., 'Organized 50+ job applications')",
            "Keep text large enough to read at thumbnail size",
        ],
    )


def generate_image_brief(niche: str, format_str: str, tone: str) -> ImageBrief:
    images = [
        _hero_prompt(niche, format_str, tone),
        _feature_prompt(niche, format_str, tone),
        _lifestyle_prompt(niche, format_str, tone),
        _detail_prompt(niche, format_str, tone),
        _comparison_prompt(niche, format_str, tone),
        _social_proof_prompt(niche, format_str, tone),
    ]
    return ImageBrief(
        generated_at=datetime.now(timezone.utc).isoformat(),
        niche=niche,
        format_str=format_str,
        tone=tone,
        images=images,
        etsy_guidelines=ETSY_GUIDELINES,
    )


def brief_to_dict(brief: ImageBrief) -> dict:
    return {
        "generated_at": brief.generated_at,
        "niche": brief.niche,
        "format": brief.format_str,
        "tone": brief.tone,
        "etsy_guidelines": brief.etsy_guidelines,
        "images": [
            {
                "name": img.name,
                "purpose": img.purpose,
                "ratio": img.ratio,
                "dimensions": img.dimensions,
                "prompt": img.prompt,
                "tips": img.tips,
            }
            for img in brief.images
        ],
    }


def write_image_brief(base_dir: Path, niche: str, format_str: str, tone: str) -> Path:
    brief = generate_image_brief(niche, format_str, tone)
    data = brief_to_dict(brief)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = niche.lower().replace(" ", "-")[:40]
    output_dir = base_dir / "outputs" / f"{timestamp}-{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / "image-brief.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
