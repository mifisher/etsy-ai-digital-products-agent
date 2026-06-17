# Etsy AI Digital Products Agent

CLI tool for generating Etsy draft-listing packages for AI-assisted digital products.

Current scope:
- Takes a product niche, buyer, format, and tone
- Generates a structured product brief
- Produces Etsy listing metadata, tags, disclosure copy, and a file manifest
- Saves outputs to timestamped folders for manual review
- Optional competitor-informed generation (pass `--research` with competitor JSON)
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

## Competitor Research Mode

Feed in competitor listing data to get price, tag, and title suggestions informed by the market:

```bash
PYTHONPATH=src python3 -m etsy_agent.cli \
  --product-niche "Budget meal planner for busy parents" \
  --buyer "Working parents with 2+ kids" \
  --format "Notion + PDF" \
  --tone "Simple, friendly, no-fluff" \
  --research outputs/sample_competitors_meal_planner.json \
  --research-out outputs/meal_planner_insights.json
```

The `--research` file should be a JSON array of competitor objects:

```json
[
  {
    "title": "Competitor Listing Title",
    "url": "https://www.etsy.com/listing/...",
    "price": 12.99,
    "description": "Snippet or description text",
    "site_name": "www.etsy.com"
  }
]
```

### How to gather competitor data

Etsy blocks direct scraping, so use a search engine via OpenClaw `web_search` or manually:

```
web_search: "site:etsy.com meal planner notion template"
```

Save the results to JSON and pass them to `--research`.

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

## Image Brief Mode

Generate detailed image prompts and Etsy guidelines for your listing photos:

```bash
PYTHONPATH=src python3 -m etsy_agent.cli \
  --product-niche "Budget meal planner for busy parents" \
  --buyer "Working parents with 2+ kids" \
  --format "Notion + PDF" \
  --tone "Simple, friendly, no-fluff" \
  --image-brief
```

This produces `image-brief.json` with 6 image types:
- **Hero Image** — main thumbnail (1:1, 2000x2000px)
- **Feature Breakdown** — what's included (4:3, 2000x1500px)
- **Lifestyle / In-Use** — product in context (4:3)
- **Detail / Close-Up** — quality showcase (1:1)
- **Before / After** — transformation story (4:3)
- **Social Proof** — testimonials or results (4:3)

Each includes a detailed prompt, design tips, and dimensions.

## Layout

- `src/etsy_agent/cli.py` - CLI entrypoint
- `src/etsy_agent/generator.py` - deterministic + optional LLM package generator
- `src/etsy_agent/research.py` - competitor analysis and market insights
- `src/etsy_agent/image_brief.py` - image prompt and brief generation
- `outputs/` - generated draft packages

## Near-Term Next Steps

1. Add Etsy OAuth and draft-listing upload when credentials are ready.
2. Add automated competitor-data gathering via search APIs.
3. Generate actual listing images using the image briefs with AI image models.
