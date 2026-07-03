from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

from etsy_agent.generator import ProductInput, write_package
from etsy_agent.research import load_competitor_data, analyze_competitors, save_insights
from etsy_agent.image_brief import write_image_brief
from etsy_agent import etsy_client


def cmd_generate(args: argparse.Namespace) -> None:
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


def cmd_auth(args: argparse.Namespace) -> None:
    try:
        config = etsy_client.EtsyConfig.from_env()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    verifier, challenge = etsy_client._generate_pkce()
    state = secrets.token_urlsafe(16)
    auth_url = etsy_client.build_auth_url(
        client_id=config.client_id,
        redirect_uri=config.redirect_uri,
        scopes=["listings_r", "listings_w", "shops_r"],
        state=state,
        code_challenge=challenge,
    )

    print("=== Etsy OAuth Setup ===")
    print(f"1. Open this URL in your browser:\n   {auth_url}")
    print(f"2. After authorizing, Etsy will redirect to your callback URL.")
    print(f"3. Copy the 'code' query parameter from the redirect URL.")
    print(f"4. Run: PYTHONPATH=src python3 -m etsy_agent.cli exchange --code <CODE>")
    print(f"\nPKCE verifier (save this securely): {verifier}")
    print(f"State: {state}")

    token_path = Path(args.token_path) if args.token_path else Path("etsy_token.json")
    metadata = {
        "verifier": verifier,
        "state": state,
        "redirect_uri": config.redirect_uri,
        "token_path": str(token_path),
    }
    token_path.with_suffix(".oauth.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"\nOAuth metadata saved to {token_path.with_suffix('.oauth.json')}")


def cmd_exchange(args: argparse.Namespace) -> None:
    try:
        config = etsy_client.EtsyConfig.from_env()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    oauth_file = Path(args.oauth_file or "etsy_token.oauth.json")
    if not oauth_file.exists():
        print(f"Error: OAuth metadata file not found: {oauth_file}", file=sys.stderr)
        sys.exit(1)

    metadata = json.loads(oauth_file.read_text())
    verifier = metadata["verifier"]
    token_path = Path(metadata.get("token_path", "etsy_token.json"))

    print(f"Exchanging code for token...")
    token = etsy_client.exchange_code(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=metadata["redirect_uri"],
        code=args.code,
        code_verifier=verifier,
    )
    etsy_client.save_token(token, token_path)
    print(f"Token saved to {token_path}")
    print(f"Access token expires in {token.get('expires_in', 'unknown')} seconds")


def cmd_upload(args: argparse.Namespace) -> None:
    package_path = Path(args.package)
    package = json.loads((package_path / "package.json").read_text())
    listing = package["listing"]

    payload = etsy_client.build_draft_payload(
        title=listing["title"],
        description=listing["description"],
        price=listing["price_recommendation_usd"],
        who_made=listing.get("who_made", "i_did"),
        when_made=listing.get("when_made", "made_to_order"),
        taxonomy_id=listing.get("taxonomy_id", 12476),
        is_supply=listing.get("is_supply", False),
        listing_type=listing.get("type", "download"),
        tags=listing.get("tags", []),
    )

    if args.dry_run:
        print("=== DRY RUN ===")
        print("Would create draft listing with payload:")
        print(json.dumps(payload, indent=2))
        return

    try:
        config = etsy_client.EtsyConfig.from_env()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    token_path = Path(args.token_path or "etsy_token.json")
    if not token_path.exists():
        print(f"Error: Token file not found: {token_path}", file=sys.stderr)
        print("Run 'auth' first, then 'exchange' to get a token.", file=sys.stderr)
        sys.exit(1)

    token = etsy_client.load_token(token_path)
    client = etsy_client.EtsyClient(config, token["access_token"])

    print("Creating draft listing...")
    result = client.create_draft_listing(payload)
    print(f"Draft listing created: {result}")

    listing_id = result.get("listing_id")
    if listing_id:
        print(f"\nNext steps:")
        print(f"1. Upload listing images to Etsy")
        print(f"2. Upload digital file via uploadListingFile")
        print(f"3. Activate: PYTHONPATH=src python3 -m etsy_agent.cli activate --listing-id {listing_id}")


def cmd_activate(args: argparse.Namespace) -> None:
    try:
        config = etsy_client.EtsyConfig.from_env()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    token_path = Path(args.token_path or "etsy_token.json")
    token = etsy_client.load_token(token_path)
    client = etsy_client.EtsyClient(config, token["access_token"])

    if args.dry_run:
        print(f"=== DRY RUN ===")
        print(f"Would set listing {args.listing_id} type to 'download'")
        return

    result = client.update_listing(args.listing_id, {"type": "download"})
    print(f"Listing updated: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Etsy AI Digital Products Agent")
    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate a draft listing package")
    gen_parser.add_argument("--product-niche", required=True)
    gen_parser.add_argument("--buyer", required=True)
    gen_parser.add_argument("--format", dest="product_format", required=True)
    gen_parser.add_argument("--tone", required=True)
    gen_parser.add_argument("--research", type=Path, help="Path to competitor JSON data")
    gen_parser.add_argument("--research-out", type=Path, help="Path to write competitor analysis insights JSON")
    gen_parser.add_argument("--image-brief", action="store_true", help="Also generate a detailed image brief")
    gen_parser.set_defaults(func=cmd_generate)

    # auth
    auth_parser = subparsers.add_parser("auth", help="Start Etsy OAuth flow")
    auth_parser.add_argument("--token-path", default="etsy_token.json", help="Path to save token metadata")
    auth_parser.set_defaults(func=cmd_auth)

    # exchange
    exchange_parser = subparsers.add_parser("exchange", help="Exchange OAuth code for token")
    exchange_parser.add_argument("--code", required=True, help="Authorization code from Etsy redirect")
    exchange_parser.add_argument("--oauth-file", default="etsy_token.oauth.json", help="OAuth metadata file from auth step")
    exchange_parser.set_defaults(func=cmd_exchange)

    # upload
    upload_parser = subparsers.add_parser("upload", help="Upload a package as Etsy draft listing")
    upload_parser.add_argument("--package", required=True, help="Path to generated package directory")
    upload_parser.add_argument("--token-path", default="etsy_token.json", help="Path to OAuth token file")
    upload_parser.add_argument("--dry-run", action="store_true", help="Show payload without uploading")
    upload_parser.set_defaults(func=cmd_upload)

    # activate
    activate_parser = subparsers.add_parser("activate", help="Set listing type to download (digital)")
    activate_parser.add_argument("--listing-id", required=True, help="Etsy listing ID")
    activate_parser.add_argument("--token-path", default="etsy_token.json", help="Path to OAuth token file")
    activate_parser.add_argument("--dry-run", action="store_true", help="Show action without uploading")
    activate_parser.set_defaults(func=cmd_activate)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
