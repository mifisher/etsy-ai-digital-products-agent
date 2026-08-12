from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

API_BASE = "https://api.etsy.com/v3/application"


def _urlopen_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


class EtsyPublicClient:
    """Read-only Etsy client using static key auth (no OAuth).

    api_key must be the combined "keystring:shared_secret" form; the
    keystring alone returns 403.
    """

    def __init__(
        self,
        api_key: str,
        fetch: Callable[[str, dict], dict] | None = None,
        min_interval: float = 0.25,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self._fetch = fetch or _urlopen_json
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._last_call = 0.0

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key}

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{API_BASE}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                return self._fetch(url, self._headers())
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                if not retryable or attempt == self.max_retries - 1:
                    raise
                time.sleep(2**attempt)
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def search_active(self, keywords: str, limit: int = 20) -> dict:
        return self._get(
            "/listings/active",
            {"keywords": keywords, "limit": limit, "sort_on": "score"},
        )

    def shop_active_listings(self, shop_id: str) -> list[dict]:
        data = self._get(f"/shops/{shop_id}/listings/active", {"limit": 100})
        return data.get("results", [])
