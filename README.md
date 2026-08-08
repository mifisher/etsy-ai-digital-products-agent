# Etsy AI Digital Products Agent

CLI tool for generating Etsy draft-listing packages for AI-assisted digital products.

Current scope:
- Takes a product niche, buyer, format, and tone
- Generates a structured product brief
- Produces Etsy listing metadata, tags, disclosure copy, and a file manifest
- Saves outputs to timestamped folders for manual review
- Optional competitor-informed generation (pass `--research` with competitor JSON)
- Optional LLM-backed generation via OpenAI (set `ETSY_USE_LLM=1`)
- Optional Etsy OAuth + draft listing upload (requires Etsy developer credentials)

This project is intentionally portfolio-first and draft-first. It does not auto-publish to Etsy without review.

## Quick Start

```bash
cd etsy-ai-digital-products-agent
PYTHONPATH=src python3 -m etsy_agent.cli generate \
  --product-niche "AI job search planner for product managers" \
  --buyer "Senior PMs and AI PM candidates" \
  --format "Google Sheets + PDF" \
  --tone "Practical, premium, operator-grade"
```

Outputs are written to `outputs/<timestamp>-<slug>/`.

## Competitor Research Mode

Feed in competitor listing data to get price, tag, and title suggestions informed by the market:

```bash
PYTHONPATH=src python3 -m etsy_agent.cli generate \
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

Set `ETSY_USE_LLM=1` to generate copy with an LLM. Two providers are supported
(both use the `openai` package — `pip install openai`):

**Moonshot (Kimi):**

```bash
export ETSY_USE_LLM=1
export ETSY_LLM_PROVIDER=moonshot
export MOONSHOT_API_KEY="your-moonshot-key"
# optional: export ETSY_LLM_MODEL=kimi-k2-0711-preview

PYTHONPATH=src python3 -m etsy_agent.cli generate \
  --product-niche "Budget meal planner for busy parents" \
  --buyer "Working parents with 2+ kids" \
  --format "Notion + PDF" \
  --tone "Simple, friendly, no-fluff"
```

**OpenAI:**

```bash
export ETSY_USE_LLM=1
export ETSY_LLM_PROVIDER=openai   # (default)
export OPENAI_API_KEY="your-openai-key"
```

| Variable | Purpose | Default |
|---|---|---|
| `ETSY_LLM_PROVIDER` | `moonshot` or `openai` | `openai` |
| `MOONSHOT_API_KEY` / `OPENAI_API_KEY` | provider API key | — |
| `ETSY_LLM_MODEL` | model override | `kimi-k2-0711-preview` / `gpt-4.1` |
| `MOONSHOT_BASE_URL` | Moonshot endpoint | `https://api.moonshot.ai/v1` |

Keep keys out of git: put these `export`s in a git-ignored `set-env.sh` and
`source set-env.sh`. Never hardcode a key in tracked files.

If the LLM call fails (quota, network), the tool exits with a clear error so you can fall back to deterministic mode.

## Image Brief Mode

Generate detailed image prompts and Etsy guidelines for your listing photos:

```bash
PYTHONPATH=src python3 -m etsy_agent.cli generate \
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

## Etsy OAuth & Draft Listing Upload

### 1. Register an Etsy Developer App

1. Go to https://www.etsy.com/developers/your-apps
2. Create a new app
3. Note your **keystring** (client_id) and **shared secret** (client_secret)
4. Set a redirect URI (e.g., `https://localhost:3000/oauth/callback`)

### 2. Set environment variables

```bash
export ETSY_CLIENT_ID="your-keystring"
export ETSY_CLIENT_SECRET="your-shared-secret"
export ETSY_SHOP_ID="your-shop-id"
export ETSY_REDIRECT_URI="https://localhost:3000/oauth/callback"
```

Find your shop ID by visiting your shop page and checking the URL, or via the Etsy API.

### 3. Authenticate

```bash
PYTHONPATH=src python3 -m etsy_agent.cli auth
```

This prints an OAuth URL. Open it in your browser, authorize the app, then copy the `code` from the redirect URL.

### 4. Exchange code for token

```bash
PYTHONPATH=src python3 -m etsy_agent.cli exchange --code "YOUR_CODE"
```

This saves `etsy_token.json` for future API calls.

### 5. Upload a draft listing

```bash
PYTHONPATH=src python3 -m etsy_agent.cli upload \
  --package outputs/20260617T000000Z-your-product \
  --dry-run
```

Remove `--dry-run` to actually create the draft listing on Etsy.

### 6. Activate as digital download

After uploading images and digital files via Etsy's web UI or API:

```bash
PYTHONPATH=src python3 -m etsy_agent.cli activate --listing-id "YOUR_LISTING_ID"
```

This sets the listing type to `download` (required for digital products).

## Layout

- `src/etsy_agent/cli.py` - CLI entrypoint with generate/auth/exchange/upload/activate commands
- `src/etsy_agent/generator.py` - deterministic + optional LLM package generator
- `src/etsy_agent/research.py` - competitor analysis and market insights
- `src/etsy_agent/image_brief.py` - image prompt and brief generation
- `src/etsy_agent/etsy_client.py` - Etsy OAuth + API v3 client
- `outputs/` - generated draft packages

## Opportunity Radar

`radar/` is a separate module that searches Etsy for product niches, scores
them (quantitative signals + optional LLM judgment), and writes a weekly
markdown digest to `history/digests/`.

Run it manually:

```bash
source set-env.sh
python -m radar.run --config config/lanes.yml --history history
```

Add `--dry-run` to print the digest without writing to `history/`.

### Scheduled run

`.github/workflows/radar.yml` runs the radar every Monday (`workflow_dispatch`
is also enabled for on-demand runs) and commits the resulting digest back to
`history/`. It has `contents: write` permission and no `pull_request` trigger,
so repository secrets are never exposed to a fork PR.

Required repo secrets: `ETSY_CLIENT_ID`, `ETSY_CLIENT_SECRET`, `ETSY_SHOP_ID`,
`MOONSHOT_API_KEY`.

### Public sync

This repo is private because `history/`, `product/`, `config/lanes.yml`, and
credentials hold real business strategy and cannot be published. `sync-public.sh`
copies an explicit **allowlist** of code paths (radar module, tests, generic
workflow files, README, `config/lanes.example.yml`) into a separate public
portfolio checkout:

```bash
./sync-public.sh ~/coding-projects/etsy-ai-digital-products-agent
```

Nothing outside the allowlist is copied — adding a new file here does nothing
to the public repo until it's named in `sync-public.sh`. Always review
`git status` in the public checkout before committing.

## Near-Term Next Steps

1. Add automated competitor-data gathering via search APIs.
2. Generate actual listing images using the image briefs with AI image models.
3. Add file upload support for digital products via `uploadListingFile`.
