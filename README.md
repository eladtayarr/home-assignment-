# NexWave Mobile — Data Analyst Home Assignment

Management's concern: *"the numbers look fine on the surface, but something
feels off lately."* This repo documents the full investigation, from raw data
to the finding, dashboard, and presentation.

## How this is organized (read in this order)

| Phase | Doc | What it covers |
|---|---|---|
| 1 | [`docs/01_data_quality_memo.md`](docs/01_data_quality_memo.md) | Every data quality issue found in the 6 source CSVs, the decision made for each, and why |
| 2 | [`docs/02_data_model.md`](docs/02_data_model.md) | Star schema design, relationship diagram, Power Query (M) transformation steps |
| 3 | [`docs/03_dax_measures.md`](docs/03_dax_measures.md) | KPI selection rationale + full DAX measure library |
| 4 | [`docs/04_findings.md`](docs/04_findings.md) | The exploratory analysis and the headline finding, with evidence |
| 5 | [`docs/05_dashboard_spec.md`](docs/05_dashboard_spec.md) | Power BI dashboard build spec (3 pages, visuals, filters) |
| 6 | [`deck/NexWave_Mobile_Business_Review.pptx`](deck/NexWave_Mobile_Business_Review.pptx) | The 10-slide management presentation |

## The headline finding, in one line

A franchise dealer (MobileZone) ran a low-quality subscriber acquisition surge
in H1 2025 — 43% of that cohort had already churned by year-end — which is now
driving a company-wide churn increase and has flipped the 2025 revenue budget
from a beat to a widening miss in Q4, even though total revenue and net adds
looked fine every month all year. Full detail: `docs/04_findings.md`.

## Repo layout

```
data/raw/          the 6 original CSVs, unmodified
data/clean/         cleaned star-schema tables, ready to import into Power BI
scripts/            Python (pandas) scripts: profiling -> cleaning -> analysis
docs/               the memo, model, DAX, findings, and dashboard spec (phases 1-5)
deck/               presentation build script + the final .pptx (phase 6)
powerbi/            a Power BI Project (.pbip) with the semantic model pre-built
```

## Reproducing the analysis

```bash
pip install pandas numpy
python3 scripts/01_profile_data.py          # Phase 1: profiling
python3 scripts/02_profile_deepdive.py      # Phase 1: follow-up checks
python3 scripts/03_build_star_schema.py     # Phase 2: builds data/clean/*.csv
python3 scripts/04_exploratory_analysis.py  # Phase 4: trends, mix, budget variance
python3 scripts/05_churn_driver_analysis.py # Phase 4: isolates the dealer driver
python3 scripts/06_mobilezone_cohort_check.py  # Phase 4: cohort-quality confirmation
```

## Building the Power BI dashboard

**Fastest path:** open `powerbi/NexWave Mobile.pbip` in Power BI Desktop — it's
a pre-built semantic model (all 8 tables, 9 relationships, 21 DAX measures,
`dim_date` already marked as the Date Table). Edit one parameter to point at
your local copy of `data/clean/`, refresh, then build the 3 report pages per
`docs/05_dashboard_spec.md`. See `powerbi/README.md` for the exact steps and
important caveats (I don't have Power BI Desktop to test-open this myself).

**From scratch instead:**
1. Import the 8 tables in `data/clean/` (Get Data → Text/CSV), or replicate the
   equivalent Power Query steps documented in `docs/02_data_model.md`.
2. Build the relationships per the diagram in `docs/02_data_model.md` §3; mark
   `dim_date[date]` as the Date Table.
3. Paste in the measures from `docs/03_dax_measures.md`.
4. Build the 3 pages per `docs/05_dashboard_spec.md`.

## Rebuilding the presentation

```bash
cd deck && npm install pptxgenjs && node build_deck.js
```
