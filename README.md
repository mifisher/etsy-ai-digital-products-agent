# Etsy AI Digital Products Agent

CLI tool for generating Etsy draft-listing packages for AI-assisted digital products.

Current scope:
- Takes a product niche, buyer, format, and tone
- Generates a structured product brief
- Produces Etsy listing metadata, tags, disclosure copy, and a file manifest
- Saves outputs to timestamped folders for manual review
- Optional LLM-backed generation via OpenAI (set `ETSY_USE_LLM=1`)

This project is intentionally portfolio-first and draft-first. It does not auto-publish to Etsy.

## Quick Start

```bash
cd /data/.openclaw/workspace/etsy-ai-digital-products-agent
PYTHONPATH=src python3 -m etsy_agent.cli \
  --product-niche "AI job search planner for product managers" \
  --buyer "Senior PMs and AI PM candidates" \
  --format "Google Sheets + PDF" \
  --tone "Practical, premium, operator-grade"
```

Outputs are written to `outputs/<timestamp>-<slug>/`.

## LLM Mode

Set `ETSY_USE_LLM=1` to use OpenAI for generation (requires `OPENAI_API_KEY`):

```bash
ETSY_USE_LLM=1 PYTHONPATH=src python3 -m etsy_agent.cli \
  --product-niche "Budget meal planner for busy parents" \
  --buyer "Working parents with 2+ kids" \
  --format "Notion + PDF" \
  --tone "Simple, friendly, no-fluff"
```

If the LLM call fails (quota, network), the tool exits with a clear error so you can fall back to deterministic mode.

## Layout

- `src/etsy_agent/cli.py` - CLI entrypoint
- `src/etsy_agent/generator.py` - deterministic + optional LLM package generator
- `outputs/` - generated draft packages

## Near-Term Next Steps

1. Add competitor-research ingestion for title/tag guidance.
2. Add Etsy OAuth and draft-listing upload when credentials are ready.
3. Add image-brief generation for listing mockups.
4. Add pricing research based on niche competitiveness.
