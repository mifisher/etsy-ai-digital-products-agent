from __future__ import annotations

import argparse
import json
from pathlib import Path

from etsy_agent.generator import ProductInput, write_package
from etsy_agent.research import load_competitor_data, analyze_competitors, save_insights
from etsy_agent.image_brief import write_image_brief


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Etsy digital product draft package.")
    parser.add_argument("--product-niche", required=True)
    parser.add_argument("--buyer", required=True)
    parser.add_argument("--format", dest="product_format", required=True)
    parser.add_argument("--tone", required=True)
    parser.add_argument("--research", type=Path, help="Path to competitor JSON data (from web search results)")
    parser.add_argument("--research-out", type=Path, help="Path to write competitor analysis insights JSON")
    parser.add_argument("--image-brief", action="store_true", help="Also generate a detailed image brief")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    product_input = ProductInput(
        product_niche=args.product_niche,
        buyer=args.buyer,
        product_format=args.product_format,
        tone=args.tone,
    )

    competitor_insights = None
    if args.research:
        listings = load_competitor_data(args.research)
        competitor_insights = analyze_competitors(listings)
        if args.research_out:
            save_insights(competitor_insights, args.research_out)
            print(f"Research insights written to {args.research_out}")
        else:
            print("--- Competitor Insights ---")
            print(json.dumps(competitor_insights, indent=2))
            print("--- End Insights ---")

    project_root = Path(__file__).resolve().parents[2]
    output_dir = write_package(project_root, product_input, competitor_insights)
    print(f"Package: {output_dir}")

    if args.image_brief:
        brief_path = write_image_brief(
            project_root, product_input.product_niche, product_input.product_format, product_input.tone
        )
        print(f"Image brief: {brief_path}")


if __name__ == "__main__":
    main()
