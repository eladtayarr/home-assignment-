# Data Quality Memo — NexWave Mobile Dataset

**Purpose:** document every data quality issue found while profiling the six source
files, the decision made for each, and the reasoning — so every number in the final
dashboard/deck can be defended.

**Source files profiled:** `customers.csv`, `subscribers.csv`, `monthly_billing.csv`,
`dealers.csv`, `price_plans.csv`, `budget.csv`. Full profiling output:
`scripts/01_profile_data.py` / `scripts/02_profile_deepdive.py` (raw console output
kept for reference, not committed).

## 1. Table shapes at a glance

| Table | Rows | Grain | Notes |
|---|---|---|---|
| customers | 34,000 | 1 row / customer | `customer_id`, `segment` (A–D), `city` (24), `district` (5) |
| subscribers | 51,143 | 1 row / line (subscriber) | `subscriber_id`, `customer_id`, `dealer_code`, `plan_code`, `join_date`, `churn_date` |
| monthly_billing | 727,540 | 1 row / subscriber / month | `subscriber_id`, `billing_month` (2023‑07 → 2025‑12, 30 months), `billed_amount` |
| dealers | 10 | 1 row / dealer | `dealer_code`, `dealer_name`, `dealer_type`, `city` |
| price_plans | 36 (35 distinct) | 1 row / plan | `plan_code`, `plan_name`, `plan_family`, `monthly_list_price` |
| budget | 4 | 1 row / district (2025 only) | 12 monthly columns, single line item "Service revenue" |

No nulls anywhere except `subscribers.churn_date` (65.2% null = still active) and
`dealers.city` (1 row, the online channel — expected).

## 2. Issues found, investigated, and resolved

### 2.1 `dealer_code` formatting inconsistency (subscribers.csv vs dealers.csv) — **fix**

`dealers.csv` uses a clean canonical form: `DLR-01` … `DLR-10`. `subscribers.csv`
contains **39 distinct raw spellings** of the same 10 dealers:

- Case variants: `dlr-01` vs `DLR-01`
- Missing leading zero: `DLR-1` vs `DLR-01`
- Trailing whitespace: `"DLR-01 "`

Example: the codes `DLR-01`, `DLR-01 `, `DLR-1`, `dlr-01` all refer to the same
dealer. This affects **7,466 of 51,143 subscriber rows (14.6%)** — too large to ignore
and large enough that "dealer performance" cuts would silently under-count 9 of the 10
dealers if left as-is.

**Decision:** standardize with `TRIM → UPPERCASE → zero-pad the numeric suffix to 2
digits` before joining to the dealer dimension. After normalization, all 39 raw values
collapse to exactly the 10 codes in `dealers.csv` with **zero unmatched values** —
confirming this is purely a formatting artifact, not a data integrity problem (no
subscriber points to a dealer that doesn't exist).

### 2.2 Duplicate `plan_code` in price_plans.csv — **fix (dedupe)**

`PLN-S100` appears twice:

| plan_code | plan_name | plan_family | monthly_list_price |
|---|---|---|---|
| PLN-S100 | Smart 100 | Smart | 55 |
| PLN-S100 | Smart100 (legacy name) | Smart | 55 |

Same family and price — this is a **relabeling artifact** (an old plan name kept in
the source extract), not a conflicting definition. There is no case in the file where
the same `plan_code` maps to two different prices/families.

**Decision:** de-duplicate on `plan_code`, keep the row with the current-looking name
("Smart 100"), and drop the legacy-name duplicate. Documented here as an alias so it's
traceable if questioned.

### 2.3 Plan catalog sprawl (25 of 35 plans are "legacy/plus" T-codes) — **flag, not fixed**

`price_plans.csv` has 10 "core" plans (`PLN-S100/S200/S300`, `PLN-UMAX`, `PLN-U69`,
`PLN-B40/B60`, `PLN-YTH`, `PLN-FAM`, `PLN-SNR`) and **25 additional `PLN-T01`…`PLN-T25`
codes** whose names carry "Legacy" or "Plus" and whose family/price bands overlap the
core plans almost exactly (e.g. three separate Basic plans at 31/32/40/41/44/60).
**10,295 of 51,143 subscribers (20%)** are still active on a T-series code.

This is not an error — it's a legitimate reflection of years of grandfathered pricing —
but it is a real modeling decision: T-series plans are kept as distinct rows in the
plan dimension (so historic pricing stays correct) and rolled up by `plan_family` for
any plan-mix analysis, otherwise 35 near-duplicate plan names would fragment every
chart. Flagged as a business observation for the findings (plan governance / pricing
simplification opportunity), not treated as a data cleanup item.

### 2.4 `budget.csv` district grouping doesn't match `customers.csv` district — **fix (bridge mapping)**

- `budget.csv` districts: `Center, Haifa, North, Jerusalem & South`
- `customers.csv` / derived dealer districts: `Center, Haifa, North, Jerusalem, South`

The budget was built with Jerusalem and South combined into one district, while the
operational tables keep them separate (and city→district mapping in `customers.csv`
is internally 100% consistent — every city maps to exactly one district, so this isn't
a labeling bug on the operational side).

**Decision:** add a `budget_district` bridge column to the district dimension:
`Jerusalem → "Jerusalem & South"`, `South → "Jerusalem & South"`, everything else
maps to itself. All budget-vs-actual comparisons use `budget_district`; all other
district-level cuts (churn, ARPU, dealer mix, etc.) keep the granular 5-district view.
This is called out explicitly on the budget page of the dashboard so nobody mistakes
"Jerusalem & South" actuals for a 6th district.

### 2.5 Dealers have no `district` field — **fix (derive)**

`dealers.csv` gives `city` but not `district`. Since `customers.csv` proves the
city→district mapping is 1:1 and consistent, the same lookup is applied to `dealers.city`
to derive `dealers.district`. The one online dealer (`DLR-09`, no city) is labeled
district = "Online / N/A" rather than dropped, so it still appears in dealer-type cuts.

### 2.6 Billing after `churn_date` — **investigated, not an error**

727,540 billing rows checked against `subscribers.churn_date`:

- **14,108 rows** fall in the *same calendar month* as the churn date but *after* the
  exact churn day — i.e. a final, partial-month invoice for the month the customer
  left. This is expected telco behavior (bill up to the day of disconnection).
- **0 rows** fall in any month *after* the churn month.

**Decision:** no exclusion needed. Documented assumption: a subscriber is treated as
"active in month M" if `churn_date` is null OR `churn_date` falls in month M or later
— i.e. the churn month itself still counts as active/billed, churn takes effect at
month-end for reporting purposes. This is the standard convention for monthly telco
churn reporting and avoids double-counting or under-billing revenue in the churn month.

### 2.7 Subscribers with zero billing rows — **investigated, explained by data window, flagged**

**3,678 of 51,143 subscribers (7.2%)** have no rows at all in `monthly_billing.csv`.
Investigation: **all 3,678** have a `churn_date` populated, and **all 3,678 churned
before 2023‑07‑01** — the first month `monthly_billing.csv` covers. In other words,
their entire subscription lifecycle (join → churn) happened before the billing fact
table's window begins; there was never a month for them to be billed inside this
extract.

**Decision:** treat 2023‑07 as the effective start of usable history for any
billing/revenue/ARPU/churn-rate measure. These 3,678 subscribers stay in the
`subscribers` dimension (they're real, valid records — useful for tenure and
join/plan/dealer-mix analysis of that period) but are naturally excluded from any
measure that sums or filters `monthly_billing`, since they contribute no rows there.
This is called out as an assumption rather than silently producing a "0 revenue,
100% churned" cohort with no context.

### 2.8 Referential integrity — clean

Checked and **zero problems found** on:
- `subscribers.customer_id` → all exist in `customers.csv`
- `subscribers.plan_code` → all exist in `price_plans.csv`
- `subscribers.dealer_code` (after §2.1 normalization) → all exist in `dealers.csv`
- `monthly_billing.subscriber_id` → all exist in `subscribers.csv` (no orphan billing)
- No duplicate `customer_id`, `subscriber_id`, or `(subscriber_id, billing_month)` keys
- No `churn_date` earlier than `join_date`
- No non-numeric, negative, or zero `billed_amount` values
- No unparseable dates in any date column

### 2.9 `billed_amount` vs plan list price — **investigated, explained, assumption documented**

`billed_amount` is not always equal to the subscriber's `plan_code` list price:
- 50% of rows are exactly at list price; 78% are within ±5%.
- 3.5% of rows are below 50% of list price — consistent with partial-month proration
  in join/churn months.
- 11.2% of rows are above 105% of list price — consistent with usage overage or
  add‑ons, which are not broken out as separate line items in this extract.

**Decision/assumption:** `billed_amount` is used as-is as the net revenue figure per
subscriber per month. No attempt is made to decompose it into base fee vs. overage,
since no such breakdown exists in the source data — this is stated explicitly as an
assumption in the methodology slide.

### 2.10 Customer → subscriber cardinality — **modeling input, not an issue**

68.8% of customers (23,390 of 34,000) have exactly one subscriber (line); 31.2%
(10,610 customers) have 2–5 lines. This confirms `customers` and `subscribers` are
genuinely different grains (an account vs. a line) and must be modeled as separate
dimension tables joined 1‑to‑many, not merged into one table. See Phase 2 model.

## 3. Summary of decisions

| # | Issue | Decision | Type |
|---|---|---|---|
| 2.1 | dealer_code formatting (39 variants) | Normalize (trim/upper/zero-pad) before join | Fix |
| 2.2 | Duplicate PLN-S100 row | Drop legacy-name duplicate | Fix |
| 2.3 | 25 legacy T-series plans (plan sprawl) | Keep, roll up by plan_family for mix analysis | Flag / assumption |
| 2.4 | budget district ≠ customer district | Add `budget_district` bridge mapping | Fix |
| 2.5 | dealers missing district | Derive from city via customers' city→district map | Fix |
| 2.6 | Billing after churn_date | Confirmed same-month partial bill only; define "active" as churn month inclusive | Assumption |
| 2.7 | 3,678 subscribers with no billing rows | Explained by pre-2023-07 lifecycle, outside billing window; exclude from billing measures, keep in dimension | Assumption |
| 2.8 | Referential integrity | All clean — no action needed | Verified |
| 2.9 | billed_amount vs list price dispersion | Use billed_amount as-is as net revenue; no overage breakout available | Assumption |
| 2.10 | Customer:subscriber is 1:many | Model as separate dimensions | Design input |

All decisions above are carried into the Phase 2 cleaning script
(`scripts/03_build_star_schema.py`) and the Power Query M steps documented in
`docs/02_data_model.md`.
