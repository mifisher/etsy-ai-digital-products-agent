# Etsy AI Digital Products Agent

Two tools for running a digital-products shop on Etsy:

1. **Opportunity Radar** — a scheduled agent that searches Etsy for underserved
   product niches, scores them against live marketplace data, diagnoses why your
   own listings are or are not selling, and files a weekly digest telling you the
   single best thing to do next.
2. **Listing generator** — a CLI that turns a product niche into an Etsy listing
   package (title, 13 tags, description, AI disclosure, pricing) and can create
   the draft listing over the Etsy API.

Fork it, point it at your own shop and your own niches, and it will run itself.
Nothing publishes to Etsy without your review.

[See a sample weekly digest →](docs/sample-digest.md)

---

## Fork and run the radar

**1. Fork this repo**, then clone your fork.

**2. Get Etsy API credentials.** Create an app at
[etsy.com/developers](https://www.etsy.com/developers/register). You need the
keystring and the shared secret. Note that Etsy expects them **combined** in the
`x-api-key` header as `keystring:shared_secret` — the keystring alone returns a
403, which this client already handles.

**3. Configure your niches.**

```bash
cp config/lanes.example.yml config/lanes.yml   # config/lanes.yml is gitignored
```

Edit it: set `shop_id` (find it at `/v3/application/shops?shop_name=YOURSHOP`),
then replace the example lanes with the niches you want researched. Each lane has:

| Field | Meaning |
|---|---|
| `keywords` | What the radar searches Etsy for |
| `credibility` | 0–1. How believable *your* copy would be in this niche. A deliberate human judgement — asking the model to rate your own credibility just invites flattery. |
| `brand_fit` | `my_shop` or `new_shop`. Routes the recommendation. |

**4. Run it locally.**

```bash
cp set-env.example.sh set-env.sh    # gitignored; fill in your keys
source set-env.sh
pip install pyyaml openai
PYTHONPATH=. python -m radar.run --dry-run   # --dry-run writes nothing
```

**5. Schedule it.** Copy `docs/radar.public.yml` to
`.github/workflows/radar.yml`, add your secrets under *Settings → Secrets and
variables → Actions*, and uncomment the `schedule:` block. It ships
dispatch-only so forking never starts a cron job you did not ask for.

Each run commits a digest to `history/digests/` **and files it as a GitHub
issue**, so GitHub emails it to you. A weekly report nobody reads is worth
nothing; that step is what closes the loop.

> **Keep your strategy private.** Your real niche list, digests and decision
> history are business intelligence. `config/lanes.yml` and `history/` are
> gitignored here for that reason. If you intend to publish your fork, note that
> **GitHub Actions logs and artifacts on public repos are readable by anyone** —
> run the radar from a private repo and mirror only code outward.
> `sync-public.sh` does this by allowlist, and refuses to run if it finds
> private strings in what it is about to copy.

## How the scoring works

Each niche gets a score in `[0,1]`, built from two halves. The split exists
because neither half is trustworthy alone: pure marketplace math cannot tell
whether a pain is urgent or expensive, and a language model asked to estimate
demand will simply invent it.

```
quantitative = 0.40·demand + 0.40·gap + 0.20·price
    demand — mean favorites across the sampled listings
    gap    — demand ÷ active listing count, i.e. underserved-ness
    price  — median price

qualitative  = 0.30·pain_urgency + 0.30·willingness_to_pay
             + 0.25·differentiation + 0.15·credibility
             (LLM-judged, while looking at the real competitor data)

score = 0.45·quantitative + 0.35·qualitative + 0.20·ease_to_create
```

Every weight and threshold lives in `config/lanes.yml`, so you can retune
without touching code; each group is validated to sum to 1.0 at load time.

Two details worth knowing if you modify this:

- **Demand uses the mean, not the median.** Etsy favorite counts are heavy-tailed
  and mostly zero — a real sample was `[0, 0, 34, 1475, 470]`. The median
  collapses to ~0 for nearly every niche and erases the signal. The tail *is* the
  signal. Price still uses the median, where robustness to one outlier is correct.
- **Normalization is min-max within a single run**, so scores are comparative for
  that run rather than absolute across time.

If the LLM is unavailable — no key, no credit, provider outage — the run
degrades to quantitative-only scoring, marks the digest as provisional, and
still ships. It never fails the week.

## Listing generator (CLI)

A separate tool from the radar: turns one niche into a listing package.

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
# optional: export ETSY_LLM_MODEL=moonshot-v1-32k   (kimi-* models fail JSON mode)

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
| `ETSY_LLM_MODEL` | model override | `moonshot-v1-32k` / `gpt-4.1` |
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

**Radar** — the scheduled agent:

| File | Responsibility |
|---|---|
| `radar/run.py` | Orchestrates a run: collect → judge → score → digest → persist |
| `radar/config.py` | Loads lanes, weights and thresholds; validates weight sums |
| `radar/etsy_api.py` | Read-only Etsy client with throttling and retries |
| `radar/collectors.py` | Turns API responses into signals; diagnoses your listings |
| `radar/scoring.py` | Normalization, the quantitative model, verdicts, routing |
| `radar/llm.py` | Grounded qualitative judgement, with a safe no-op fallback |
| `radar/history.py` | Snapshots, decision log, rejection cooldown |
| `radar/digest.py` | Renders the weekly markdown report |

**Listing generator** — the CLI:

| File | Responsibility |
|---|---|
| `src/etsy_agent/cli.py` | `generate` / `auth` / `exchange` / `upload` / `activate` |
| `src/etsy_agent/generator.py` | Deterministic + optional LLM package generation |
| `src/etsy_agent/research.py` | Competitor analysis and market insights |
| `src/etsy_agent/image_brief.py` | Listing-image prompts and specs |
| `src/etsy_agent/etsy_client.py` | Etsy OAuth + API v3 write client |

Run the tests with `python -m pytest tests/ -v`.

## Known limitations

Worth knowing before relying on this:

- **No search-volume data.** Etsy's API does not expose it, and this project
  deliberately avoids paid keyword tools. Demand is inferred from favorites on
  competing listings — a proxy, not a measurement.
- **Scores are comparative, not absolute.** Min-max normalization happens within
  a single run, so a 0.78 this week and a 0.78 next week are not the same thing.
- **The model's prose is weaker than its numbers.** Ratings are grounded in real
  marketplace data; the narrative rationale can still be thin, or conflate supply
  with demand. Read it as a prompt for your own thinking, not a conclusion.
- **Nothing builds the product.** The radar tells you what to make. Making it is
  still your job.
- **Rejected niches are hidden for 30 days** by default (`reject_cooldown_days`),
  so a digest can look sparse after a few runs. Lower it while tuning.

## Near-Term Next Steps

1. Templatize product generation so a recommendation can become a draft SKU.
2. Generate listing images from the image briefs with an image model.
3. Add file upload for digital products via `uploadListingFile`.
