"""Polls Google Places across every grid point, filters, and writes restaurants.csv."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .places_client import PlacesClient
from .regions import (
    NEARBY_RADIUS_METERS,
    REGIONS,
    STATE_TO_REGION,
    GridPoint,
    all_grid_points,
)


MIN_RATING_COUNT = 100


@dataclass
class Restaurant:
    place_id: str
    name: str
    address: str
    lat: float
    lng: float
    rating: float
    rating_count: int
    primary_type: str
    state: str
    region: str


def _extract_state_from_address(address: str) -> str | None:
    """Best-effort: pull the USPS state abbreviation out of a formatted address."""
    parts = [p.strip() for p in address.split(",")]
    for part in parts:
        tokens = part.split()
        for token in tokens:
            stripped = token.strip().upper()
            if len(stripped) == 2 and stripped in STATE_TO_REGION:
                return stripped
    return None


def _place_to_restaurant(place: dict, fallback_state: str) -> Restaurant | None:
    place_id = place.get("id")
    rating = place.get("rating")
    rating_count = place.get("userRatingCount")
    primary_type = place.get("primaryType", "")
    if not (place_id and rating is not None and rating_count is not None):
        return None
    if primary_type != "chinese_restaurant":
        return None
    if rating_count < MIN_RATING_COUNT:
        return None

    address = place.get("formattedAddress", "")
    state = _extract_state_from_address(address) or fallback_state
    region = STATE_TO_REGION.get(state)
    if region is None:
        return None

    location = place.get("location", {})
    return Restaurant(
        place_id=place_id,
        name=(place.get("displayName") or {}).get("text", ""),
        address=address,
        lat=location.get("latitude", 0.0),
        lng=location.get("longitude", 0.0),
        rating=float(rating),
        rating_count=int(rating_count),
        primary_type=primary_type,
        state=state,
        region=region,
    )


def collect_all(
    client: PlacesClient,
    output_path: Path,
    progress_every: int = 50,
) -> dict[str, int]:
    """Sweep every grid point in every region, dedupe, filter, write CSV.

    Returns a per-region count of restaurants that passed filtering.
    """
    grid = all_grid_points()
    total_points = len(grid)
    print(f"Sweeping {total_points} grid points across {len(REGIONS)} regions...")

    seen: dict[str, Restaurant] = {}
    for i, point in enumerate(grid, start=1):
        response = client.search_nearby_chinese(
            lat=point.lat, lng=point.lng, radius_m=NEARBY_RADIUS_METERS,
        )
        for place in response.get("places", []) or []:
            restaurant = _place_to_restaurant(place, fallback_state=point.state)
            if restaurant and restaurant.place_id not in seen:
                seen[restaurant.place_id] = restaurant
        if i % progress_every == 0 or i == total_points:
            print(
                f"  [{i}/{total_points}] api_calls={client.stats.requests_made} "
                f"cache_hits={client.stats.cache_hits} unique_restaurants={len(seen)}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "place_id", "name", "address", "lat", "lng",
            "rating", "rating_count", "primary_type", "state", "region",
        ])
        for r in seen.values():
            writer.writerow([
                r.place_id, r.name, r.address, r.lat, r.lng,
                r.rating, r.rating_count, r.primary_type, r.state, r.region,
            ])

    per_region: dict[str, int] = {region: 0 for region in REGIONS}
    for r in seen.values():
        per_region[r.region] += 1
    print("\nRestaurants passing filter per region:")
    for region, count in per_region.items():
        print(f"  {region:>8}: {count}")
    print(f"Wrote {len(seen)} restaurants to {output_path}")
    return per_region


def estimate_calls() -> int:
    """How many API calls a fresh (uncached) collect would make."""
    return len(all_grid_points())


def _count_points(points: list[GridPoint], state: str) -> int:
    return sum(1 for p in points if p.state == state)
