import urllib.error

import pytest

from radar.etsy_api import EtsyPublicClient


def test_search_active_builds_url_and_headers():
    calls = []

    def fake_fetch(url, headers):
        calls.append((url, headers))
        return {"count": 42, "results": [{"title": "x"}]}

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)
    out = client.search_active("job search tracker", limit=5)

    assert out["count"] == 42
    url, headers = calls[0]
    assert "/application/listings/active" in url
    assert "keywords=job+search+tracker" in url
    assert "limit=5" in url
    assert headers["x-api-key"] == "key:secret"


def test_shop_active_listings_returns_results_list():
    def fake_fetch(url, headers):
        assert "/shops/12345678/listings/active" in url
        return {"count": 1, "results": [{"listing_id": 1, "views": 6}]}

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)
    listings = client.shop_active_listings("12345678")

    assert listings == [{"listing_id": 1, "views": 6}]


def test_retries_on_429_then_succeeds(monkeypatch):
    """Verify retry logic retries on 429 rate limit and succeeds on subsequent attempt."""
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(
                url="http://api.etsy.com/test",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=None
            )
        return {"count": 1, "results": []}

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)
    result = client.search_active("test", limit=5)

    assert result["count"] == 1
    assert len(attempts) == 3


def test_does_not_retry_on_403(monkeypatch):
    """Verify no retry on 403 Forbidden (permanent error, would waste quota)."""
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        raise urllib.error.HTTPError(
            url="http://api.etsy.com/test",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None
        )

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)

    with pytest.raises(urllib.error.HTTPError):
        client.search_active("test", limit=5)

    assert len(attempts) == 1


def test_retries_on_url_error_then_succeeds(monkeypatch):
    """A transient DNS/TCP failure (urllib.error.URLError) must be retried
    with the same backoff as HTTPError, not propagate and kill the run."""
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.URLError("temporary failure in name resolution")
        return {"count": 1, "results": []}

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)
    result = client.search_active("test", limit=5)

    assert result["count"] == 1
    assert len(attempts) == 3


def test_retries_on_timeout_error_then_succeeds(monkeypatch):
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        if len(attempts) < 2:
            raise TimeoutError("timed out")
        return {"count": 1, "results": []}

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)
    result = client.search_active("test", limit=5)

    assert result["count"] == 1
    assert len(attempts) == 2


def test_does_not_retry_on_403_after_url_error_change(monkeypatch):
    """Regression guard: HTTPError is a URLError subclass. Adding a
    URLError except clause must not accidentally make a 403 retryable —
    it must still raise on the very first attempt."""
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        raise urllib.error.HTTPError(
            url="http://api.etsy.com/test",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0)

    with pytest.raises(urllib.error.HTTPError):
        client.search_active("test", limit=5)

    assert len(attempts) == 1


def test_raises_after_exhausting_retries(monkeypatch):
    """Verify HTTPError propagates after max_retries attempts exhausted."""
    monkeypatch.setattr("radar.etsy_api.time.sleep", lambda _: None)

    attempts = []

    def fake_fetch(url, headers):
        attempts.append(1)
        raise urllib.error.HTTPError(
            url="http://api.etsy.com/test",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None
        )

    client = EtsyPublicClient("key:secret", fetch=fake_fetch, min_interval=0, max_retries=3)

    with pytest.raises(urllib.error.HTTPError):
        client.search_active("test", limit=5)

    assert len(attempts) == 3
