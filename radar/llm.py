from __future__ import annotations

import json
import os
from typing import Any

from radar.config import Lane
from radar.models import Judgment, LaneSignals

SYSTEM_PROMPT = (
    "You evaluate Etsy digital-product opportunities. You are given REAL "
    "marketplace data for one niche. Judge only from that data plus general "
    "knowledge of the buyer. Do not invent demand figures.\n\n"
    "The seller can produce exactly one kind of product: multi-tab Google "
    "Sheets systems plus a branded PDF guide and listing images. Anything "
    "else (printable art, fonts, SVGs, physical goods) is buildability="
    "'needs_new_capability'.\n\n"
    "Return ONLY a JSON object with keys: pain_urgency, willingness_to_pay, "
    "differentiation, ease_to_create (all floats 0-1); buildability "
    "('factory' or 'needs_new_capability'); buyer, product_format, "
    "differentiation_angle, why_this_could_sell (strings); price_range_usd "
    "(array of two integers)."
)


def build_client() -> tuple[Any, str]:
    import openai

    provider = os.getenv("ETSY_LLM_PROVIDER", "moonshot").strip().lower()
    if provider == "moonshot":
        api_key = os.getenv("MOONSHOT_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("MOONSHOT_API_KEY is not set")
        base_url = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")
        model = os.getenv("ETSY_LLM_MODEL", "kimi-k2-0711-preview")
        return openai.OpenAI(api_key=api_key, base_url=base_url), model

    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is not set")
    return openai.OpenAI(), os.getenv("ETSY_LLM_MODEL", "gpt-4.1")


def _clamp(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


def _user_prompt(lane: Lane, signals: LaneSignals) -> str:
    titles = "\n".join(f"- {t}" for t in signals.sample_titles[:10])
    return (
        f"Niche keyword: {signals.keyword}\n"
        f"Active competing listings: {signals.active_listings}\n"
        f"Median favorites (top {signals.sample_size}): {signals.median_favorites}\n"
        f"Median price: ${signals.median_price:.2f}\n"
        f"Competitor titles:\n{titles}\n"
    )


def judge_lane(
    client: Any, model: str, lane: Lane, signals: LaneSignals
) -> Judgment | None:
    """Return qualitative judgment, or None if the LLM is unusable.

    Callers fall back to quantitative-only scoring on None so a provider
    outage never blocks the weekly digest.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(lane, signals)},
            ],
            temperature=0.4,
        )
        data = json.loads(response.choices[0].message.content)
        return Judgment(
            pain_urgency=_clamp(data["pain_urgency"]),
            willingness_to_pay=_clamp(data["willingness_to_pay"]),
            differentiation=_clamp(data["differentiation"]),
            ease_to_create=_clamp(data["ease_to_create"]),
            buildability=str(data.get("buildability", "needs_new_capability")),
            buyer=str(data.get("buyer", "")),
            product_format=str(data.get("product_format", "")),
            differentiation_angle=str(data.get("differentiation_angle", "")),
            why_this_could_sell=str(data.get("why_this_could_sell", "")),
            price_range_usd=[int(x) for x in data.get("price_range_usd", [0, 0])],
        )
    except Exception:
        return None
