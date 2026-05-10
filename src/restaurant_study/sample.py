"""Random-samples 50 restaurants per region with a fixed seed."""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from .regions import REGIONS


SAMPLE_SIZE = 50
RANDOM_SEED = 42


def sample_all(input_path: Path, output_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    rng = random.Random(RANDOM_SEED)

    samples: list[pd.DataFrame] = []
    for region in REGIONS:
        region_df = df[df["region"] == region].sort_values("place_id").reset_index(drop=True)
        n = len(region_df)
        if n < SAMPLE_SIZE:
            raise RuntimeError(
                f"Region {region!r} has only {n} restaurants after filtering; "
                f"need at least {SAMPLE_SIZE}. Re-run `collect` with more coverage "
                f"or relax filters."
            )
        indices = rng.sample(range(n), SAMPLE_SIZE)
        samples.append(region_df.iloc[indices].assign(sample_index=indices))
        print(f"  {region:>8}: sampled 50 of {n}")

    result = pd.concat(samples, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Wrote sample to {output_path}")
    return result
