# Etsy AI Digital Products Agent

CLI scaffold for generating an Etsy draft-listing package for AI-assisted digital products.

Current scope:
- Takes a product niche, buyer, format, and tone
- Generates a structured product brief
- Produces Etsy listing metadata, tags, disclosure copy, and a file manifest
- Saves outputs to timestamped folders for manual review

This project is intentionally portfolio-first and draft-first. It does not auto-publish to Etsy.

## Quick Start

```bash
cd /data/.openclaw/workspace/etsy-ai-digital-products-agent
python3 -m etsy_agent.cli \
  --product-niche "AI job search planner for product managers" \
  --buyer "Senior PMs and AI PM candidates" \
  --format "Google Sheets + PDF" \
  --tone "Practical, premium, operator-grade"
```

Outputs are written to `outputs/<timestamp>-<slug>/`.

## Layout

- `src/etsy_agent/cli.py` - CLI entrypoint
- `src/etsy_agent/generator.py` - deterministic package generator
- `outputs/` - generated draft packages

## Near-Term Next Steps

1. Add model-backed generation behind an environment-variable switch.
2. Add competitor-research ingestion for title/tag guidance.
3. Add Etsy OAuth and draft-listing upload when credentials are ready.
4. Add image-brief generation for listing mockups.
