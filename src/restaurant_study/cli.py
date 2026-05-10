"""CLI entry point for restaurant-study."""

from __future__ import annotations

import argparse
from pathlib import Path

from .analyze import analyze
from .collect import collect_all, estimate_calls
from .places_client import PlacesClient, load_api_key
from .sample import sample_all


# Rough SKU pricing per Google Maps Platform documentation. Pro-tier Nearby
# Search is around $32 per 1,000 requests once the $200/month credit is spent.
COST_PER_1K_REQUESTS_USD = 32.0
FREE_CREDIT_USD = 200.0


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = DATA_DIR / "results"
RESTAURANTS_CSV = RESULTS_DIR / "restaurants.csv"
SAMPLE_CSV = RESULTS_DIR / "sample.csv"


def _build_client(args: argparse.Namespace) -> PlacesClient:
    api_key = None if args.dry_run else load_api_key()
    return PlacesClient(
        api_key=api_key,
        cache_dir=CACHE_DIR,
        dry_run=args.dry_run,
        max_calls=args.max_calls,
    )


def cmd_collect(args: argparse.Namespace) -> None:
    total = estimate_calls()
    est_cost = total * COST_PER_1K_REQUESTS_USD / 1000.0
    print(f"A fresh collect would issue up to {total} Nearby Search requests.")
    print(
        f"Estimated raw cost: ${est_cost:,.2f}. "
        f"With the ${FREE_CREDIT_USD:.0f}/month Google Maps Platform credit, "
        f"that's ${max(0.0, est_cost - FREE_CREDIT_USD):.2f} out-of-pocket "
        f"if the credit is otherwise unused."
    )
    if args.dry_run:
        print("--dry-run set; no API calls will be made.")
        return
    client = _build_client(args)
    collect_all(client, RESTAURANTS_CSV)


def cmd_sample(args: argparse.Namespace) -> None:
    sample_all(RESTAURANTS_CSV, SAMPLE_CSV)


def cmd_analyze(args: argparse.Namespace) -> None:
    analyze(SAMPLE_CSV, RESULTS_DIR)


def cmd_all(args: argparse.Namespace) -> None:
    cmd_collect(args)
    if args.dry_run:
        return
    cmd_sample(args)
    cmd_analyze(args)


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Estimate API calls and cost without hitting the network.",
    )
    parser.add_argument(
        "--max-calls", type=int, default=None,
        help="Abort if this many uncached API calls are issued.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="restaurant-study")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_collect = subparsers.add_parser("collect", help="Poll Google Maps.")
    _add_common_flags(p_collect)
    p_collect.set_defaults(func=cmd_collect)

    p_sample = subparsers.add_parser("sample", help="Randomly sample 50/region.")
    _add_common_flags(p_sample)
    p_sample.set_defaults(func=cmd_sample)

    p_analyze = subparsers.add_parser("analyze", help="Run chi-square + make chart.")
    _add_common_flags(p_analyze)
    p_analyze.set_defaults(func=cmd_analyze)

    p_all = subparsers.add_parser("all", help="collect + sample + analyze.")
    _add_common_flags(p_all)
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
