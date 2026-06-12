from __future__ import annotations

import argparse
from pathlib import Path

from etsy_agent.generator import ProductInput, write_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Etsy digital product draft package.")
    parser.add_argument("--product-niche", required=True)
    parser.add_argument("--buyer", required=True)
    parser.add_argument("--format", dest="product_format", required=True)
    parser.add_argument("--tone", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    product_input = ProductInput(
        product_niche=args.product_niche,
        buyer=args.buyer,
        product_format=args.product_format,
        tone=args.tone,
    )
    project_root = Path(__file__).resolve().parents[2]
    output_dir = write_package(project_root, product_input)
    print(output_dir)


if __name__ == "__main__":
    main()
