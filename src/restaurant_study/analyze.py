"""Chi-square test for homogeneity + segmented bar chart."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from .regions import REGIONS
from .sample import _load_exclusions, _normalize_name


RATING_CATEGORIES = ["<=3.5", "3.6-4.0", "4.1-4.5", "4.6-5.0"]
SIGNIFICANCE_LEVEL = 0.10


def categorize(rating: float) -> str:
    if rating <= 3.5:
        return "<=3.5"
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


def _plot_per_region(contingency: pd.DataFrame, out_path: Path) -> None:
    """One bar chart per region: observed relative freq + expected as overlaid lines."""
    counts = contingency.drop(columns=["Total"])
    row_totals = counts.sum(axis=1)
    col_totals = counts.sum(axis=0)
    grand_total = col_totals.sum()
    # Under H0, expected relative freq is identical across regions: col_total / grand_total.
    expected_rel = (col_totals / grand_total).to_numpy()

    regions = list(counts.index)
    fig, axes = plt.subplots(1, len(regions), figsize=(4 * len(regions), 5),
                             sharey=True)
    x = np.arange(len(RATING_CATEGORIES))
    for ax, region in zip(axes, regions):
        observed_rel = counts.loc[region].to_numpy() / row_totals.loc[region]
        bars = ax.bar(x, observed_rel, color="#1f77b4", label="Observed")
        y_top = max(observed_rel.max(), expected_rel.max()) * 1.15
        # Expected overlay: short horizontal segment centered on each bar.
        for i, exp in enumerate(expected_rel):
            ax.hlines(exp, i - 0.4, i + 0.4, colors="#d62728", linewidth=2.5,
                      label="Expected" if i == 0 else None)
            label_y = max(exp, observed_rel[i]) + y_top * 0.025
            ax.text(i, label_y, f"{exp:.3f}", ha="center", va="bottom",
                    fontsize=9, color="#d62728", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(RATING_CATEGORIES, rotation=20)
        ax.set_title(region)
        ax.set_ylim(0, y_top)
        for bar, value in zip(bars, observed_rel):
            if value > 0.03:
                ax.text(bar.get_x() + bar.get_width() / 2, y_top * 0.01,
                        f"{value:.3f}", ha="center", va="bottom", fontsize=9,
                        color="white", fontweight="bold")
            else:
                ax.text(bar.get_x() + bar.get_width() / 2, value + y_top * 0.01,
                        f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    axes[0].set_ylabel("Relative Frequency")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("Star-Rating Distribution by Region — Observed vs. Expected")
    plt.tight_layout(rect=(0, 0, 0.92, 1))
    fig.legend(handles, labels, loc="center right", bbox_to_anchor=(1.0, 0.5))
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def visualize(
    sample_path: Path,
    out_dir: Path,
    exclusions_path: Path | None = None,
) -> Path:
    sample_df = pd.read_csv(sample_path)
    if exclusions_path is not None:
        sample_df = _apply_exclusions(sample_df, exclusions_path)
    contingency = build_contingency(sample_df)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "per_region_distribution.png"
    _plot_per_region(contingency, out_path)
    print(f"Wrote: {out_path}")
    return out_path


def _apply_exclusions(sample_df: pd.DataFrame, exclusions_path: Path) -> pd.DataFrame:
    """Drop rows in sample_df that appear in exclusions.txt; print what was dropped."""
    excluded_ids, excluded_names = _load_exclusions(exclusions_path)
    if not excluded_ids and not excluded_names:
        return sample_df

    normalized = sample_df["name"].map(_normalize_name)
    mask_id = sample_df["place_id"].isin(excluded_ids)
    mask_name = normalized.isin(excluded_names)
    drop_mask = mask_id | mask_name
    if not drop_mask.any():
        return sample_df

    dropped = sample_df.loc[drop_mask, ["place_id", "name", "region"]]
    print(f"\nDropping {len(dropped)} restaurant(s) from analysis "
          f"per {exclusions_path.name}:")
    for _, row in dropped.iterrows():
        print(f"  [{row['region']:>8}]  {row['place_id']}  {row['name']}")
    print()
    return sample_df.loc[~drop_mask].reset_index(drop=True)


def analyze(
    sample_path: Path,
    out_dir: Path,
    test_state: str | None = None,
    exclusions_path: Path | None = None,
) -> dict:
    sample_df = pd.read_csv(sample_path)
    if exclusions_path is not None:
        sample_df = _apply_exclusions(sample_df, exclusions_path)
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
