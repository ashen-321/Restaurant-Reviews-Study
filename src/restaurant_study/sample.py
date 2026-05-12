"""Random-samples 50 restaurants per region with a fixed seed."""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from .regions import REGIONS, STATE_TO_REGION


SAMPLE_SIZE = 75
RANDOM_SEED = 42


def _load_exclusions(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            ids.add(line)
    return ids


def sample_all(
    input_path: Path,
    output_path: Path,
    test_state: str | None = None,
    exclusions_path: Path | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    if exclusions_path is not None:
        excluded = _load_exclusions(exclusions_path)
        if excluded:
            before = len(df)
            df = df[~df["place_id"].isin(excluded)]
            print(f"Excluded {before - len(df)} restaurants via {exclusions_path.name}")
    rng = random.Random(RANDOM_SEED)

    previous_ids: set[str] = set()
    if output_path.exists():
        try:
            prev = pd.read_csv(output_path, usecols=["place_id"])
            previous_ids = set(prev["place_id"].astype(str))
        except (ValueError, KeyError):
            pass

    if test_state:
        target_regions = [STATE_TO_REGION[test_state]]
    else:
        target_regions = list(REGIONS)

    samples: list[pd.DataFrame] = []
    for region in target_regions:
        region_df = df[df["region"] == region].sort_values("place_id").reset_index(drop=True)
        n = len(region_df)
        if n == 0:
            raise RuntimeError(
                f"Region {region!r} has no restaurants after filtering. "
                "Re-run `collect` or check the state filter."
            )
        take = min(SAMPLE_SIZE, n)
        if n < SAMPLE_SIZE and not test_state:
            raise RuntimeError(
                f"Region {region!r} has only {n} restaurants after filtering; "
                f"need at least {SAMPLE_SIZE}. Re-run `collect` with more coverage "
                f"or relax filters."
            )
        indices = rng.sample(range(n), take)
        chosen = region_df.iloc[indices].assign(sample_index=indices)
        samples.append(chosen)
        print(f"  {region:>8}: sampled {take} of {n}")

    result = pd.concat(samples, ignore_index=True)
    if previous_ids:
        result["newly_added"] = ~result["place_id"].isin(previous_ids)
        added = int(result["newly_added"].sum())
        print(f"New restaurants vs. previous sample: {added}")
    else:
        result["newly_added"] = True
        print("No previous sample found; marking all rows as newly_added=True.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Wrote sample to {output_path}")
    return result
