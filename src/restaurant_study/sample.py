"""Random-samples 50 restaurants per region with a fixed seed."""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from .regions import REGIONS, STATE_TO_REGION


SAMPLE_SIZE = 50
RANDOM_SEED = 42


def sample_all(
    input_path: Path,
    output_path: Path,
    test_state: str | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    rng = random.Random(RANDOM_SEED)

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
        samples.append(region_df.iloc[indices].assign(sample_index=indices))
        print(f"  {region:>8}: sampled {take} of {n}")

    result = pd.concat(samples, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Wrote sample to {output_path}")
    return result
