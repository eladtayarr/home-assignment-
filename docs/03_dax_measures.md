# KPI Definitions & DAX Measure Library

## Why these KPIs and not others

The brief is "the numbers look fine on the surface, but something feels off" —
that phrasing points at **trend and mix shifts a single point-in-time total would
hide**, not at raw totals. The measure set below is deliberately narrow and
covers five questions a mobile-operator management team actually asks weekly:

1. Is revenue growing, and is growth accelerating or decelerating? (Revenue + time
   intelligence)
2. Are we keeping the subscriber base we already have? (churn / net adds)
3. Is each subscriber worth more or less over time, and does that vary by
   segment/plan? (ARPU)
4. Are we on track against what Finance budgeted, by district? (budget variance)
5. Is the base quietly shifting in ways that matter (legacy plan concentration)?
   (mix)

Deliberately **not** built: per-city drill-down measures (city is redundant with
district for this dataset — 24 cities roll up cleanly into 5 districts, no
information is lost by using district as the standard geography), a revenue
decomposition into base-fee vs. overage (source data doesn't support it — see
memo §2.9), and a customer-level (as opposed to subscriber-level) ARPU (the
industry-standard ARPU definition is per subscriber/line, which is what the
billing fact table's grain actually supports without assumptions).

## Model prerequisites for these measures

- `dim_date` is marked as the model's **Date Table** (column `date`) — required
  for every time-intelligence function below.
- `fact_billing` is confirmed **gap-free**: every subscriber has exactly one
  billing row for every month between (max of join month, 2023‑07) and (churn
  month, or 2025‑12 if still active) — verified during Phase 2 build. This means
  `DISTINCTCOUNT(fact_billing[subscriber_id])` is a reliable point-in-time active
  count; no special handling of missing months is needed.
- Budget-comparison measures (`Budget Revenue`, `Budget Variance …`) are only
  meaningful when sliced by `dim_district[district]` and `dim_date` — there is no
  budget breakdown by segment, plan, or dealer in the source data, so using these
  measures against those dimensions would imply a precision the data doesn't have.
  Not disabled structurally, but called out here and on the dashboard.

## Calculated columns

These are already built into the cleaned CSVs / M queries in Phase 2
(`status`, `in_billing_window`, `tenure_days` on `dim_subscriber`; `is_legacy_plan`
on `dim_plan`; the district bridge columns). If you'd rather add them as native
Power BI calculated columns instead of relying on the Power Query layer, the
equivalents are:

```DAX
Subscriber Status =
IF(ISBLANK(dim_subscriber[churn_date]), "Active", "Churned")

Tenure Days =
DATEDIFF(
    dim_subscriber[join_date],
    COALESCE(dim_subscriber[churn_date], DATE(2025,12,31)),
    DAY
)

Is Legacy Plan =
LEFT(dim_plan[plan_code], 5) = "PLN-T"
```

## Measure library

### Revenue & growth

```DAX
Total Revenue =
SUM(fact_billing[billed_amount])
```
*What it is:* net billed revenue for whatever subscriber/plan/dealer/district/date
filter is in context. This is the base measure nearly everything else builds on.
*Why it matters:* the single top-line number management opens the dashboard to see.

```DAX
Revenue MoM % =
VAR CurrentRevenue = [Total Revenue]
VAR PriorMonthRevenue =
    CALCULATE([Total Revenue], DATEADD(dim_date[date], -1, MONTH))
RETURN
    DIVIDE(CurrentRevenue - PriorMonthRevenue, PriorMonthRevenue)
```
*Why it matters:* "something feels off lately" is a recent-trend complaint —
month-over-month is the first place a sudden shift shows up, well before it's
visible in a flat annual total.

```DAX
Revenue YoY % =
VAR CurrentRevenue = [Total Revenue]
VAR PriorYearRevenue =
    CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[date]))
RETURN
    DIVIDE(CurrentRevenue - PriorYearRevenue, PriorYearRevenue)
```
*Caveat:* only defined from **2024‑07 onward** — `fact_billing` starts 2023‑07, so
any month before 2024‑07 has no prior-year comparison and the measure correctly
returns blank there. Documented so nobody reads a blank YoY tile as zero growth.

```DAX
Revenue Trailing 3M =
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -3, MONTH)
)

Revenue Trailing 12M =
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -12, MONTH)
)
```
*Why it matters:* smooths single-month noise so a real trend break isn't
mistaken for random month-to-month variance, and vice versa.

### Subscriber base & churn

```DAX
Active Subscribers (EOP) =
VAR LastDateInContext = MAX(dim_date[date])
VAR TargetMonthStart = DATE(YEAR(LastDateInContext), MONTH(LastDateInContext), 1)
RETURN
CALCULATE(
    DISTINCTCOUNT(fact_billing[subscriber_id]),
    fact_billing[date] = TargetMonthStart
)
```
*What it is:* subscribers billed in the last month of whatever period is
selected — an end-of-period snapshot, not a sum across the period (so selecting
a full quarter still returns a headcount, not an inflated multi-month total).
*Why it matters:* the base "how big is the business right now" number every
other subscriber KPI is built from.

```DAX
Active Subscribers (BOP) =
VAR LastDateInContext = MAX(dim_date[date])
VAR TargetMonthStart = DATE(YEAR(LastDateInContext), MONTH(LastDateInContext), 1)
VAR PriorMonthStart = EDATE(TargetMonthStart, -1)
RETURN
CALCULATE(
    DISTINCTCOUNT(fact_billing[subscriber_id]),
    fact_billing[date] = PriorMonthStart
)
```
*Why it matters:* the denominator churn rate needs — subscribers who were
already on the books *before* this period's churn happened.

```DAX
New Subscribers (Gross Adds) =
VAR PeriodStart = MIN(dim_date[date])
VAR PeriodEnd = MAX(dim_date[date])
RETURN
CALCULATE(
    COUNTROWS(dim_subscriber),
    dim_subscriber[join_date] >= PeriodStart,
    dim_subscriber[join_date] <= PeriodEnd
)
```

```DAX
Churned Subscribers =
VAR PeriodStart = MIN(dim_date[date])
VAR PeriodEnd = MAX(dim_date[date])
RETURN
CALCULATE(
    COUNTROWS(dim_subscriber),
    dim_subscriber[churn_date] >= PeriodStart,
    dim_subscriber[churn_date] <= PeriodEnd
)
```
*Why gross adds and churn separately:* net adds alone hides whether a flat
number is "nothing is happening" or "we're losing as many as we win" — a very
different story for management.

```DAX
Net Subscriber Adds =
[New Subscribers (Gross Adds)] - [Churned Subscribers]
```

```DAX
Churn Rate (Monthly %) =
DIVIDE([Churned Subscribers], [Active Subscribers (BOP)])
```
*Why it matters:* the single most-watched health metric for any subscription
business — expressed as a rate (not a raw count) so it's comparable across
periods and segments regardless of base size.

```DAX
Churn Rate Trailing 3M (Avg) =
AVERAGEX(
    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -3, MONTH),
    [Churn Rate (Monthly %)]
)
```
*Why it matters:* single-month churn rate is noisy (billing-cycle timing,
one bad dealer batch); a trailing average is what actually indicates a
sustained problem worth acting on.

### ARPU

```DAX
ARPU =
DIVIDE([Total Revenue], [Active Subscribers (EOP)])
```
*What it is:* average revenue per subscriber for the period in context.
*Why it matters:* separates "we have fewer/more subscribers" from "each
subscriber is worth less/more" — two very different root causes for a revenue
change, and the second one is invisible in Total Revenue or subscriber count
alone.

```DAX
ARPU MoM % =
VAR CurrentARPU = [ARPU]
VAR PriorMonthARPU = CALCULATE([ARPU], DATEADD(dim_date[date], -1, MONTH))
RETURN
    DIVIDE(CurrentARPU - PriorMonthARPU, PriorMonthARPU)
```

### Budget vs. actual (district/month grain only — see prerequisites above)

```DAX
Budget Revenue =
SUM(fact_budget[budget_amount])
```

```DAX
Budget Variance =
[Total Revenue] - [Budget Revenue]
```

```DAX
Budget Variance % =
DIVIDE([Budget Variance], [Budget Revenue])
```

```DAX
Budget Variance YTD =
VAR ActualYTD = CALCULATE([Total Revenue], DATESYTD(dim_date[date]))
VAR BudgetYTD = CALCULATE([Budget Revenue], DATESYTD(dim_date[date]))
RETURN
    ActualYTD - BudgetYTD
```
*Why it matters:* this is literally what "budget" means to Finance — a single
month can be noisy (a heavy churn month, a promo), but a widening YTD gap is
the kind of thing that "looks fine on the surface" until someone adds it up.

### Plan mix

```DAX
% Subscribers on Legacy Plans =
VAR LegacyActive =
    CALCULATE(
        COUNTROWS(dim_subscriber),
        dim_plan[is_legacy_plan] = TRUE,
        dim_subscriber[status] = "Active"
    )
VAR TotalActive =
    CALCULATE(
        COUNTROWS(dim_subscriber),
        dim_subscriber[status] = "Active"
    )
RETURN
    DIVIDE(LegacyActive, TotalActive)
```
*Why it matters:* ties directly to the plan-sprawl observation in the data
quality memo (§2.3) — 20% of the active base sits on one of 25 near-duplicate
"legacy/plus" plan codes. Tracking this as a rate (not a static count) shows
whether the legacy base is shrinking (plans sunsetting naturally) or growing
(new subscribers still being sold onto discontinued-in-spirit plans, which
would be a governance problem worth flagging).

### Dealer acquisition quality (added after Phase 4 finding)

The Phase 4 investigation found that gross-adds-only dealer reporting let a
serious quality problem (MobileZone's H1‑2025 acquisition surge, 27% of that
cohort churned within 180 days vs. 6.7–10.9% for every other dealer) go
unnoticed for two quarters. These two additions turn "acquisition quality" into
a standing, ongoing measure instead of a one-time investigation.

```DAX
Churned Within 180 Days =
NOT ISBLANK(dim_subscriber[churn_date]) &&
DATEDIFF(dim_subscriber[join_date], dim_subscriber[churn_date], DAY) <= 180
```
*Calculated column on `dim_subscriber`.* Flags whether a subscriber churned
fast — within roughly six months of joining. Uses only `join_date`/`churn_date`,
already present in the model; no new import needed.

```DAX
New Subscriber Share % =
VAR PeriodStart = MIN(dim_date[date])
VAR PeriodEnd = MAX(dim_date[date])
VAR DealerAdds = [New Subscribers (Gross Adds)]
VAR CompanyAdds =
    CALCULATE(
        COUNTROWS(dim_subscriber),
        REMOVEFILTERS(dim_dealer),
        dim_subscriber[join_date] >= PeriodStart,
        dim_subscriber[join_date] <= PeriodEnd
    )
RETURN
    DIVIDE(DealerAdds, CompanyAdds)
```
*What it is:* a dealer's share of that period's total new-subscriber adds.
*Why it matters:* this is the number that would have flagged the MobileZone
problem in real time — its share of new adds jumped from a normal ~15–19% to
~40% for two consecutive quarters before any churn showed up. A sudden,
sustained jump in one dealer's acquisition share is worth a look on its own,
independent of churn.

```DAX
180-Day Cohort Churn Rate =
VAR CohortSize = COUNTROWS(dim_subscriber)
VAR CohortChurned180 =
    CALCULATE(
        COUNTROWS(dim_subscriber),
        dim_subscriber[Churned Within 180 Days] = TRUE
    )
RETURN
    DIVIDE(CohortChurned180, CohortSize)
```
*What it is:* of the subscribers who joined in the period selected (the
"cohort"), what share had already churned within 180 days of joining — sliced
by dealer, this is the acquisition-quality scorecard. **This is the single
number that isolates the MobileZone problem**: 27.1% for MobileZone's H1‑2025
cohort vs. 6.7–10.9% for every other dealer's H1‑2025 cohort.
*Usage note:* only meaningful when the date filter is set to a **join cohort
period** (e.g. "subscribers who joined in Q1 2025"), not an arbitrary reporting
period — pair it with a slicer on `dim_subscriber[join_date]`, not
`dim_date`, since this measure deliberately does not use the date-table
relationship (it needs the subscriber's *join* month, not the currently
selected *reporting* month).
