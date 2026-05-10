# Restaurant Reviews Study

Polls Google Maps for Chinese restaurant star ratings across five U.S. regions
(Pacific, Rockies, Midwest, South, Atlantic) and performs a chi-square test for
homogeneity on the resulting rating distribution table.

## Setup

```bash
conda create -n stats -c conda-forge python=3.12 requests python-dotenv pandas scipy matplotlib
conda activate stats
pip install -e .
cp .env.example .env       # then paste your Google Maps API key into .env
```

The API key needs the **Places API (New)** enabled in Google Cloud Console.
The tool caches every response to disk so re-runs do not incur additional costs.

## Usage

Estimate call count and cost for a run without requiring the Google Maps API:

```bash
restaurant-study collect --dry-run
```

Run the full pipeline (polling + sampling + analysis + charts):

```bash
restaurant-study collect          # poll Google Maps, cache results
restaurant-study sample           # filter + randomly sample 50 per region
restaurant-study analyze          # chi-square test + bar charts
```

Or run everything in one shot:

```bash
restaurant-study all
```

Outputs are saved in `data/`:
- `data/cache/` — raw API responses (delete to force a refetch from the Google Maps API)
- `data/results/restaurants.csv` — all polled restaurants after filtering
- `data/results/sample.csv` — the 50-per-region random sample
- `data/results/contingency.csv` — the 5x5 count table
- `data/results/chi_square.txt` — test statistic, p-value, expected counts
- `data/results/segmented_bar.png` — segmented bar chart across regions

## Sampling methodology

1. Grid-sweep every state with Nearby Search circles (configurable radius, default 30 km) to poll
   Chinese restaurants, deduplicated by `place_id`.
2. Filter to keep only restaurants with ≥ 100 ratings and whose Google `primary_type` is
   `chinese_restaurant` (automatically remove nearly all non-Chinese and asian fusion restaurants,
   manually check the remaining restaurants to ensure they serve exclusively Chinese food).
3. Number the valid restaurants in each region 1..N, then draw a set (default 75) unique
   indices using seeded random number generation for repeatability.
4. Bucket each rating into the corresponding category (`<3.5`, `3.6-4.0`, `4.1-4.5`, `4.6-5.0`)
   and build the 5x5 contingency table.
5. Run `scipy.stats.chi2_contingency` at α = 0.10 (df = 12) and report.
