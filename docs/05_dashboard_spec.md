# Power BI Dashboard Build Spec

**Design principle:** a clean weekly-monitoring overview page management would
actually open, plus two focused drill-down pages tied directly to the Phase 4
finding (budget impact, and the dealer/churn root cause) — not a chart dump.
Three pages total.

**Global setup**
- Import the 8 tables from `data/clean/` (or replicate via the M code in
  `docs/02_data_model.md`), build relationships exactly as in the diagram
  (`docs/02_data_model.md` §3), mark `dim_date[date]` as the Date Table, paste in
  all measures from `docs/03_dax_measures.md`.
- Theme: one accent color for "Actual", one neutral/grey for "Budget", one
  warning color (red/orange) reserved *only* for MobileZone / at-risk callouts —
  used consistently across all three pages so the eye learns it fast.
- Global slicer panel (synced across all pages via "Sync slicers"): **Month/Year**
  (from `dim_date`), **District** (from `dim_district[district]` — the 4-way
  budget-safe grain).
- Page-level extra slicers as noted per page.

---

## Page 1 — Executive Overview

**Purpose:** the page management opens every week to answer "how's the business
doing" in under 30 seconds — total health, no drill-down detail yet.

**Layout (top to bottom):**

1. **KPI card row** (6 cards, top strip):
   `Total Revenue` · `Revenue MoM %` · `Active Subscribers (EOP)` ·
   `Net Subscriber Adds` · `Churn Rate (Monthly %)` · `ARPU`
   Each card shows the current-period value with a small trend arrow/sparkline
   (Power BI card visual with a trend indicator, or KPI visual). Conditional
   color: green if MoM improving, red if degrading.

2. **Revenue trend chart** (line, full width): `Total Revenue` by month
   (2023‑07 → 2025‑12), with a second line for `Revenue Trailing 3M` to show
   the smoothed trend against the raw monthly line. Y-axis starts at 0.

3. **Churn rate trend chart** (line, half width, next to #4): `Churn Rate
   (Monthly %)` by month with `Churn Rate Trailing 3M (Avg)` overlaid. This is
   the chart that visibly shows the H2‑2025 uptick even before anyone drills in
   — deliberately placed on the overview page, not buried, since it's the
   earliest visible signal of the underlying issue.

4. **Subscriber base chart** (combo: column + line, half width, next to #3):
   `New Subscribers (Gross Adds)` and `Churned Subscribers` as columns,
   `Net Subscriber Adds` as a line, by month.

5. **Revenue & ARPU by segment** (small horizontal bar chart pair, bottom strip):
   quick mix context — not a drill-down, just orientation ("who are our
   customers").

**Filters/slicers on this page:** Month/Year range slider (defaults to trailing
12 months), District (synced). No dealer or plan slicer here — keep this page
about the whole business, not a specific cut.

**Interaction:** right-click drillthrough from the churn rate chart or the
`Churn Rate (Monthly %)` KPI card → **Dealer & Churn Driver** page (page 3),
so a viewer who notices the uptick can jump straight to "why" in one click.

---

## Page 2 — Budget Performance

**Purpose:** answer "are we on track against what Finance budgeted, and where,"
month by month, for 2025 — the page that turns the churn story into a dollar
number Finance cares about.

**Layout:**

1. **KPI card row:** `Budget Revenue` · `Total Revenue` (labeled "Actual") ·
   `Budget Variance` · `Budget Variance %` · `Budget Variance YTD`.

2. **Actual vs. Budget trend** (combo chart, full width): monthly `Total
   Revenue` (column) vs. `Budget Revenue` (line), Jan–Dec 2025 only. This is the
   chart that shows the beat-through-September / miss-from-October pattern
   directly — the visual anchor of the whole page.

3. **Variance % by district, by month** (matrix with conditional-formatting
   heatmap, districts as rows, months as columns, `Budget Variance %` as the
   value): red-shaded cells make the Q4 shift to red jump out across every
   district at once.

4. **Cumulative YTD variance** (line/area chart, full width): running
   `Budget Variance YTD` through the year — the "widening gap" framing in one
   line, ending clearly negative in December.

**Filters/slicers on this page:** Month/Year (synced), **District — must use
`dim_district[district]` (the 4-way budget-comparable grouping)**; do NOT add a
`district_detail` (5-way) slicer here — there is no budget data at that
granularity and it would silently invite an unanswerable "why is Jerusalem
different from South" question. A text note on the page states this
explicitly (mirrors memo §2.4).

**No dealer/segment/plan slicer here** — budget only exists at district/month
grain (see DAX doc prerequisites); adding those slicers would imply a precision
the source data doesn't support.

---

## Page 3 — Dealer & Churn Driver (the finding page)

**Purpose:** this is the page that answers "why" — built specifically to carry
the Phase 4 finding, not a generic dealer report.

**Layout:**

1. **Headline callout** (text box, top of page, styled distinctly — this is
   the one page allowed a narrative headline rather than only charts):
   *"MobileZone's H1‑2025 acquisition surge (~40% of new adds vs. a normal
   15–19%) is driving the company's churn increase — 27% of that cohort had
   already churned within 180 days, vs. 6.7–10.9% for every other dealer."*

2. **Churn rate by dealer over time** (multi-line chart, full width):
   `Churn Rate (Monthly %)` by month, one line per dealer (`dim_dealer[dealer_name]`
   as legend). Format MobileZone's line in the reserved warning color and bold;
   every other dealer in muted grey/neutral tones — the visual should make
   MobileZone's line impossible to miss without needing a legend read.

3. **New subscriber share by dealer over time** (100% stacked area or line
   chart, half width): `New Subscriber Share %` by month by dealer — shows the
   ~40% spike in H1‑2025 and the collapse in H2, same color treatment as #2.

4. **180-day cohort churn rate by dealer** (horizontal bar chart, ranked
   descending, half width) — the "smoking gun" chart: `180-Day Cohort Churn
   Rate` for the H1‑2025 join cohort, one bar per dealer, MobileZone's bar in
   the warning color and clearly separated from the rest (27% vs. a tight
   6.7–10.9% band for everyone else).

5. **Dealer summary table** (bottom, full width): one row per dealer —
   `dealer_type`, total subscribers acquired, `Churned Subscribers`, lifetime
   `Total Revenue`, `Churn Rate (Monthly %)` (current period), `180-Day Cohort
   Churn Rate` (H1‑2025 cohort). Sortable; MobileZone's row conditionally
   highlighted.

**Filters/slicers on this page:** Dealer (multi-select, defaults to all),
**Join cohort month/quarter** slicer on `dim_subscriber[join_date]` specifically
for the cohort-churn visual (distinct from the page-level reporting-month
slicer — labeled clearly, e.g. "Acquisition cohort" vs. "Reporting period", to
avoid confusing the two date filters that this page uniquely needs).

**Drillthrough target:** this page accepts drillthrough from Page 1's churn
KPI (pre-filters to the dealer/period that was clicked, where applicable).

---

## Why only three pages

The brief explicitly rewards "one sharp, well-supported insight" over "ten
shallow charts." A fourth page (e.g. a generic plan/segment mix explorer) was
considered and dropped: Phase 4 found plan mix and segment ARPU are normal/
structural, not part of the story, so a dedicated page for them would be
exactly the shallow chart-dump the brief warns against. That context still
lives in two small charts on Page 1 for orientation, not a full page.
