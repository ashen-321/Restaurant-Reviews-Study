# Restaurant Reviews Study

Polls Google Maps for Chinese restaurant star ratings across five U.S. regions
(Pacific, Rockies, Midwest, South, Atlantic) and performs a chi-square test for
homogeneity on the resulting 5x5 rating distribution table, per the enclosed AP
Statistics project outline.

## Setup

```bash
conda create -n stats -c conda-forge python=3.12 requests python-dotenv pandas scipy matplotlib
conda activate stats
pip install -e .
cp .env.example .env       # then paste your Google Maps API key into .env
```

The API key needs the **Places API (New)** enabled in Google Cloud Console.
Google Maps Platform includes a $200/month credit that covers roughly 5K–10K
Places calls depending on SKU; the tool caches every response to disk so
re-runs cost nothing.

## Usage

Estimate call count and cost for a run without hitting the API:

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

Outputs land in `data/`:
- `data/cache/` — raw API responses (gitignored, safe to delete to force refetch)
- `data/results/restaurants.csv` — all polled restaurants after filtering
- `data/results/sample.csv` — the 50-per-region random sample
- `data/results/contingency.csv` — the 5x5 count table
- `data/results/chi_square.txt` — test statistic, p-value, expected counts
- `data/results/segmented_bar.png` — segmented bar chart across regions

## Sampling methodology

Per the project outline:

1. Grid-sweep every state with Nearby Search circles (30 km radius) to poll
   Chinese restaurants; deduplicate by `place_id`.
2. Filter to restaurants with ≥ 100 ratings and whose Google `primary_type` is
   `chinese_restaurant` (the outline calls for excluding Chinese fusion / mixed
   restaurants — this is the closest automatic proxy; the outline also allows
   for manual re-sampling if needed).
3. Number the valid restaurants in each region 1..N, then draw 50 unique
   indices using `random.Random(seed=42)` for repeatability.
4. Round each mean rating to the nearest category (`<3.5`, `3.5`, `4.0`, `4.5`,
   `5.0`) and build the 5x5 contingency table.
5. Run `scipy.stats.chi2_contingency` at α = 0.10 (df = 16) and report.
