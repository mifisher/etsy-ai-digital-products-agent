from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API_BASE = "https://api.etsy.com/v3"


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("ascii").rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


def build_auth_url(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: str,
    code_challenge: str,
) -> str:
    """Build the Etsy OAuth authorization URL."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{ETSY_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> dict:
    """Exchange authorization code for access token."""
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }
    req = urllib.request.Request(
        ETSY_TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def refresh_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    """Refresh an expired access token."""
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    req = urllib.request.Request(
        ETSY_TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


@dataclass
class EtsyConfig:
    client_id: str
    client_secret: str
    shop_id: str
    redirect_uri: str = "https://localhost:3000/oauth/callback"

    @classmethod
    def from_env(cls) -> "EtsyConfig":
        client_id = os.getenv("ETSY_CLIENT_ID", "").strip()
        client_secret = os.getenv("ETSY_CLIENT_SECRET", "").strip()
        shop_id = os.getenv("ETSY_SHOP_ID", "").strip()
        if not client_id or not client_secret or not shop_id:
            raise RuntimeError(
                "Missing Etsy credentials. Set ETSY_CLIENT_ID, ETSY_CLIENT_SECRET, "
                "and ETSY_SHOP_ID environment variables."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            shop_id=shop_id,
            redirect_uri=os.getenv("ETSY_REDIRECT_URI", "https://localhost:3000/oauth/callback"),
        )


class EtsyClient:
    def __init__(self, config: EtsyConfig, access_token: str):
        self.config = config
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": f"{self.config.client_id}:{self.config.client_secret}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{ETSY_API_BASE}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method=method,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    def create_draft_listing(self, payload: dict) -> dict:
        """Create a draft listing."""
        path = f"/application/shops/{self.config.shop_id}/listings"
        return self._request("POST", path, payload)

    def update_listing(self, listing_id: str, payload: dict) -> dict:
        """Update a listing (e.g., set type='download')."""
        path = f"/application/shops/{self.config.shop_id}/listings/{listing_id}"
        return self._request("PATCH", path, payload)

    def get_shop(self) -> dict:
        """Get shop details."""
        path = f"/application/shops/{self.config.shop_id}"
        return self._request("GET", path)


def build_draft_payload(
    title: str,
    description: str,
    price: float,
    quantity: int = 999,
    who_made: str = "i_did",
    when_made: str = "made_to_order",
    taxonomy_id: int = 12476,
    is_supply: bool = False,
    listing_type: str = "download",
    tags: list[str] | None = None,
    image_ids: list[int] | None = None,
) -> dict:
    """Build the minimum payload for createDraftListing.

    Passing type='download' at creation marks it a digital listing, so no
    shipping profile is required. After creation you still:
      1. upload listing images
      2. upload the digital file via uploadListingFile
    """
    payload: dict = {
        "quantity": quantity,
        "title": title[:140],
        "description": description,
        "price": price,
        "who_made": who_made,
        "when_made": when_made,
        "taxonomy_id": taxonomy_id,
        "is_supply": is_supply,
        "type": listing_type,
    }
    if tags:
        payload["tags"] = tags[:13]
    if image_ids:
        payload["image_ids"] = image_ids
    return payload


def save_token(token: dict, path: Path) -> None:
    path.write_text(json.dumps(token, indent=2) + "\n", encoding="utf-8")


def load_token(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
