"""Thin wrapper around Google Places API (New) with disk caching and dry-run support."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


PLACES_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Fields we need for the study. Google bills by field-mask tier; these are all
# in the "Pro" tier or lower, which is what the $200 free credit covers most of.
SEARCH_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.rating,"
    "places.userRatingCount,"
    "places.primaryType,"
    "places.types"
)


@dataclass
class CallStats:
    requests_made: int = 0
    cache_hits: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"requests_made": self.requests_made, "cache_hits": self.cache_hits}


class PlacesClient:
    """Calls Places API (New) searchNearby; caches every response to disk."""

    def __init__(
        self,
        api_key: str | None,
        cache_dir: Path,
        dry_run: bool = False,
        max_calls: int | None = None,
    ):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.max_calls = max_calls
        self.stats = CallStats()

    def _cache_path(self, body: dict[str, Any]) -> Path:
        key = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def search_nearby_chinese(
        self,
        lat: float,
        lng: float,
        radius_m: float,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Return a searchNearby response for 'chinese_restaurant' at (lat, lng)."""
        body: dict[str, Any] = {
            "includedTypes": ["chinese_restaurant"],
            "maxResultCount": max_results,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
        }
        return self._post_cached(PLACES_SEARCH_NEARBY_URL, body)

    def _post_cached(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        cache_path = self._cache_path({"url": url, "body": body})
        if cache_path.exists():
            self.stats.cache_hits += 1
            return json.loads(cache_path.read_text())

        if self.dry_run:
            self.stats.requests_made += 1
            return {"places": []}

        if self.max_calls is not None and self.stats.requests_made >= self.max_calls:
            raise RuntimeError(
                f"--max-calls={self.max_calls} reached; stopping to protect quota."
            )
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_MAPS_API_KEY is not set. Add it to .env or export it."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": SEARCH_FIELD_MASK,
        }

        backoff = 1.0
        for attempt in range(5):
            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 200:
                self.stats.requests_made += 1
                data = response.json()
                cache_path.write_text(json.dumps(data, indent=2))
                return data
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(
                f"Places API error {response.status_code}: {response.text[:400]}"
            )
        raise RuntimeError(f"Places API failed after retries: {response.text[:400]}")


def load_api_key() -> str | None:
    """Read GOOGLE_MAPS_API_KEY, loading .env if present."""
    try:
        from dotenv import load_dotenv  # noqa: WPS433

        load_dotenv()
    except ImportError:
        pass
    return os.environ.get("GOOGLE_MAPS_API_KEY")
