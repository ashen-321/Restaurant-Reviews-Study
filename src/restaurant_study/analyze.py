"""Chi-square test for homogeneity + segmented bar chart."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from .regions import REGIONS


RATING_CATEGORIES = ["<=3.0", "3.1-3.5", "3.6-4.0", "4.1-4.5", "4.6-5.0"]
SIGNIFICANCE_LEVEL = 0.10


def categorize(rating: float) -> str:
    if rating <= 3.0:
        return "<=3.0"
    if rating <= 3.5:
        return "3.1-3.5"
    if rating <= 4.0:
        return "3.6-4.0"
    if rating <= 4.5:
        return "4.1-4.5"
    return "4.6-5.0"


def build_contingency(sample_df: pd.DataFrame) -> pd.DataFrame:
    sample_df = sample_df.assign(category=sample_df["rating"].apply(categorize))
    table = pd.crosstab(sample_df["region"], sample_df["category"])
    table = table.reindex(index=list(REGIONS), columns=RATING_CATEGORIES, fill_value=0)
    table["Total"] = table.sum(axis=1)
    return table


def run_chi_square(contingency: pd.DataFrame) -> dict:
    observed = contingency.drop(columns=["Total"]).to_numpy()
    chi2, p_value, dof, expected = stats.chi2_contingency(observed)
    return {
        "chi2": float(chi2),
        "p_value": float(p_value),
        "dof": int(dof),
        "expected": expected,
        "observed": observed,
        "reject_h0": p_value < SIGNIFICANCE_LEVEL,
        "min_expected": float(expected.min()),
    }


def write_results(
    contingency: pd.DataFrame, result: dict, out_dir: Path,
) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    contingency_path = out_dir / "contingency.csv"
    contingency.to_csv(contingency_path)

    report_path = out_dir / "chi_square.txt"
    lines = [
        "Chi-Square Test for Homogeneity",
        "=" * 40,
        "H0: the star-rating distribution of Chinese restaurants does not differ across regions.",
        "Ha: the star-rating distribution differs across at least one region.",
        f"Significance level alpha = {SIGNIFICANCE_LEVEL}",
        "",
        "Observed counts:",
        contingency.to_string(),
        "",
        "Expected counts (under H0):",
        pd.DataFrame(
            result["expected"], index=list(REGIONS), columns=RATING_CATEGORIES,
        ).round(2).to_string(),
        "",
        f"Chi-square statistic: {result['chi2']:.4f}",
        f"Degrees of freedom:   {result['dof']}",
        f"P-value:              {result['p_value']:.4g}",
        f"Minimum expected count: {result['min_expected']:.2f}"
        + ("  (Large Counts condition met)" if result['min_expected'] >= 5
           else "  (WARNING: below 5 — Large Counts condition not satisfied)"),
        "",
        (
            f"Decision: reject H0 at alpha={SIGNIFICANCE_LEVEL}. "
            "There is evidence that the star-rating distribution of Chinese "
            "restaurants differs across U.S. regions."
            if result["reject_h0"]
            else f"Decision: fail to reject H0 at alpha={SIGNIFICANCE_LEVEL}. "
            "There is not enough evidence to conclude that the star-rating "
            "distribution of Chinese restaurants differs across U.S. regions."
        ),
    ]
    report_path.write_text("\n".join(lines))

    chart_path = out_dir / "segmented_bar.png"
    _plot_segmented_bar(contingency, chart_path)

    return contingency_path, report_path, chart_path


def _plot_segmented_bar(contingency: pd.DataFrame, out_path: Path) -> None:
    counts = contingency.drop(columns=["Total"])
    percents = counts.div(counts.sum(axis=1), axis=0) * 100

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    fig, ax = plt.subplots(figsize=(9, 6))
    bottoms = np.zeros(len(percents))
    for color, category in zip(colors, RATING_CATEGORIES):
        values = percents[category].to_numpy()
        ax.bar(percents.index, values, bottom=bottoms, label=category, color=color)
        bottoms += values

    ax.set_ylabel("Percent of Restaurants")
    ax.set_ylim(0, 100)
    ax.set_title("Chinese Restaurant Star-Rating Distribution by U.S. Region")
    ax.legend(title="Rating", loc="center left", bbox_to_anchor=(1.01, 0.5))
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def analyze(sample_path: Path, out_dir: Path, test_state: str | None = None) -> dict:
    sample_df = pd.read_csv(sample_path)
    contingency = build_contingency(sample_df)
    if test_state:
        # Only one region's worth of data — chi-square for homogeneity needs ≥2
        # populations, so show the distribution instead.
        out_dir.mkdir(parents=True, exist_ok=True)
        contingency_path = out_dir / "contingency.csv"
        contingency.to_csv(contingency_path)
        print(f"\nTEST-RUN ({test_state}) — single-region distribution:\n")
        print(contingency.to_string())
        print(f"\nWrote: {contingency_path}")
        print("Chi-square test skipped (needs >= 2 regions).")
        return {"test_run": True, "contingency": contingency}

    result = run_chi_square(contingency)
    paths = write_results(contingency, result, out_dir)
    print("\n" + (out_dir / "chi_square.txt").read_text())
    print(f"\nWrote: {paths[0]}\n       {paths[1]}\n       {paths[2]}")
    return result
