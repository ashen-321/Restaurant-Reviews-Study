"""Region + state definitions and grid-point generation for Nearby Search sweeps."""

from __future__ import annotations

import math
from dataclasses import dataclass


REGIONS: dict[str, list[str]] = {
    "Pacific":  ["AK", "HI", "CA", "OR", "WA"],
    "Rockies":  ["ID", "MT", "WY", "UT", "CO", "AZ", "NM", "NV"],
    "Midwest":  ["ND", "SD", "NE", "KS", "MN", "IA", "MO", "MI", "WI", "IL", "IN", "OH"],
    "South":    ["TX", "OK", "AR", "LA", "MS", "TN", "KY", "AL", "GA", "FL"],
    "Atlantic": ["VA", "WV", "NC", "SC", "ME", "NH", "VT", "NY", "MA", "RI",
                 "CT", "PA", "DE", "MD", "NJ", "DC"],
}

STATE_TO_REGION: dict[str, str] = {
    state: region for region, states in REGIONS.items() for state in states
}


# Approximate bounding boxes (min_lat, max_lat, min_lng, max_lng) for the
# populated portion of each state. Alaska is restricted to the southern,
# populated band to avoid wasting API calls on the Arctic interior.
STATE_BBOX: dict[str, tuple[float, float, float, float]] = {
    "AK": (55.0, 62.0, -165.0, -130.0),
    "HI": (18.9, 22.3, -160.3, -154.8),
    "CA": (32.5, 42.0, -124.5, -114.1),
    "OR": (42.0, 46.3, -124.6, -116.5),
    "WA": (45.5, 49.0, -124.8, -116.9),
    "ID": (42.0, 49.0, -117.2, -111.0),
    "MT": (44.4, 49.0, -116.1, -104.0),
    "WY": (41.0, 45.0, -111.1, -104.0),
    "UT": (37.0, 42.0, -114.1, -109.0),
    "CO": (37.0, 41.0, -109.1, -102.0),
    "AZ": (31.3, 37.0, -114.8, -109.0),
    "NM": (31.3, 37.0, -109.1, -103.0),
    "NV": (35.0, 42.0, -120.0, -114.0),
    "ND": (45.9, 49.0, -104.1, -96.5),
    "SD": (42.5, 45.9, -104.1, -96.4),
    "NE": (40.0, 43.0, -104.1, -95.3),
    "KS": (37.0, 40.0, -102.1, -94.6),
    "MN": (43.5, 49.4, -97.3, -89.5),
    "IA": (40.4, 43.5, -96.7, -90.1),
    "MO": (36.0, 40.6, -95.8, -89.1),
    "MI": (41.7, 47.5, -90.5, -82.4),
    "WI": (42.5, 47.1, -92.9, -86.8),
    "IL": (36.9, 42.6, -91.5, -87.5),
    "IN": (37.8, 41.8, -88.1, -84.8),
    "OH": (38.4, 42.0, -84.9, -80.5),
    "TX": (25.8, 36.5, -106.7, -93.5),
    "OK": (33.6, 37.0, -103.0, -94.4),
    "AR": (33.0, 36.5, -94.7, -89.6),
    "LA": (28.9, 33.1, -94.1, -88.8),
    "MS": (30.1, 35.0, -91.7, -88.1),
    "TN": (34.9, 36.7, -90.4, -81.6),
    "KY": (36.5, 39.2, -89.6, -81.9),
    "AL": (30.1, 35.1, -88.5, -84.9),
    "GA": (30.3, 35.0, -85.7, -80.8),
    "FL": (24.5, 31.0, -87.6, -80.0),
    "VA": (36.5, 39.5, -83.7, -75.2),
    "WV": (37.2, 40.6, -82.7, -77.7),
    "NC": (33.8, 36.6, -84.3, -75.5),
    "SC": (32.0, 35.2, -83.4, -78.5),
    "ME": (43.1, 47.5, -71.1, -66.9),
    "NH": (42.7, 45.3, -72.6, -70.6),
    "VT": (42.7, 45.0, -73.4, -71.5),
    "NY": (40.5, 45.0, -79.8, -71.9),
    "MA": (41.2, 42.9, -73.5, -69.9),
    "RI": (41.1, 42.0, -71.9, -71.1),
    "CT": (41.0, 42.1, -73.7, -71.8),
    "PA": (39.7, 42.3, -80.5, -74.7),
    "DE": (38.4, 39.9, -75.8, -75.0),
    "MD": (37.9, 39.7, -79.5, -75.0),
    "NJ": (38.9, 41.4, -75.6, -73.9),
    "DC": (38.79, 38.99, -77.12, -76.91),
}


NEARBY_RADIUS_METERS = 45_000  # 45 km per circle (Places API max is 50 km)
_GRID_SPACING_KM = 60.0        # wider spacing; 45 km radius still overlaps


@dataclass(frozen=True)
class GridPoint:
    state: str
    lat: float
    lng: float


def _grid_for_bbox(state: str, bbox: tuple[float, float, float, float]) -> list[GridPoint]:
    min_lat, max_lat, min_lng, max_lng = bbox
    lat_step = _GRID_SPACING_KM / 111.0
    points: list[GridPoint] = []
    lat = min_lat
    while lat <= max_lat:
        lng_step = _GRID_SPACING_KM / (111.0 * max(math.cos(math.radians(lat)), 0.1))
        lng = min_lng
        while lng <= max_lng:
            points.append(GridPoint(state=state, lat=round(lat, 4), lng=round(lng, 4)))
            lng += lng_step
        lat += lat_step
    return points


def grid_points_for_state(state: str) -> list[GridPoint]:
    return _grid_for_bbox(state, STATE_BBOX[state])


def grid_points_for_region(region: str) -> list[GridPoint]:
    return [p for state in REGIONS[region] for p in grid_points_for_state(state)]


def all_grid_points() -> list[GridPoint]:
    return [p for region in REGIONS for p in grid_points_for_region(region)]


def grid_points_for_states(states: list[str]) -> list[GridPoint]:
    return [p for s in states for p in grid_points_for_state(s)]
