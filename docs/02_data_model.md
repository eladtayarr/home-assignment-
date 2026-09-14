# Data Model — Star Schema for Power BI

## 1. Design overview

Grain decisions:

- **`fact_billing`** — one row per **subscriber per calendar month** (matches the
  source `monthly_billing.csv` grain exactly; this is the finest grain the data
  supports and the level nearly every KPI needs — revenue, ARPU, churn).
- **`fact_budget`** — one row per **district per calendar month** (unpivoted from
  the wide budget file). Kept as a **separate fact table** at a coarser grain,
  related to the model only through `dim_district` and `dim_date` — it is never
  merged into `fact_billing`.
- Dimensions: `dim_customer` (account), `dim_subscriber` (line), `dim_dealer`,
  `dim_plan`, `dim_district`, `dim_date`.

### Why customer and subscriber are separate dimensions

A **customer** is an account (segment, city, district). A **subscriber** is a
**line** on that account (its own plan, dealer of acquisition, join/churn date).
31.2% of customers (10,610 of 34,000) hold more than one line — up to 5 — so
collapsing subscriber attributes onto the customer table would either duplicate
customer rows (breaking the "1 row per customer" grain other dims rely on) or lose
per-line detail (plan, dealer, churn). They are modeled as two dimensions joined
1‑to‑many: `dim_customer (1) → dim_subscriber (many)`. `fact_billing` sits at the
subscriber grain and rolls up to the customer level through that relationship.

### The district bridge (see memo §2.4)

`dim_district` holds the **4 budget-comparable groups**
(`Center`, `Haifa`, `North`, `Jerusalem & South`) — this is the only district
column with a direct relationship to `fact_budget`. Both `dim_customer` and
`dim_dealer` carry **two** district columns:

- `district` — the 4-way, budget-comparable value (FK → `dim_district`)
- `district_detail` — the original 5-way granular value (`Jerusalem` and `South`
  kept separate) — a plain attribute, **not** related to any fact table

This lets churn/ARPU/mix analysis use the finer 5-way split freely, while any
visual that also touches the budget fact must use the 4-way `district` column —
enforced structurally, not just by convention, since `fact_budget` simply has no
relationship on `district_detail`.

## 2. Tables

| Table | Grain | Key | Row count |
|---|---|---|---|
| `dim_customer` | 1 / customer | `customer_id` | 34,000 |
| `dim_subscriber` | 1 / subscriber (line) | `subscriber_id` | 51,143 |
| `dim_dealer` | 1 / dealer | `dealer_code` | 10 |
| `dim_plan` | 1 / plan | `plan_code` | 35 (deduped from 36) |
| `dim_district` | 1 / budget-comparable district | `district` | 4 |
| `dim_date` | 1 / calendar day | `date` | 915 (2023‑07‑01 → 2025‑12‑31) |
| `fact_billing` | 1 / subscriber / month | `subscriber_id` + `date` | 727,540 |
| `fact_budget` | 1 / district / month (2025 only) | `district` + `date` | 48 |

## 3. Relationship diagram

```
dim_date (1) ──────────────┬───────────────< fact_billing (many)   [date]
                            └───────────────< fact_budget  (many)   [date]

dim_district (1) ──────────< dim_customer (many)   [district]
dim_district (1) ──────────< dim_dealer   (many)   [district]
dim_district (1) ──────────< fact_budget  (many)   [district]

dim_customer (1) ───────────< dim_subscriber (many)  [customer_id]
dim_dealer   (1) ───────────< dim_subscriber (many)  [dealer_code]
dim_plan     (1) ───────────< dim_subscriber (many)  [plan_code]

dim_subscriber (1) ─────────< fact_billing (many)   [subscriber_id]
```

All relationships are **single-direction, one-to-many, filtering from the "1" side
to the "many" side** (Power BI default) — no bidirectional cross-filtering is
needed anywhere in this model. `fact_billing` and `fact_budget` never relate to
each other directly; they are compared only via measures that both reference
`dim_date` and `dim_district` (e.g. Actual Revenue rolls up subscriber→customer→
district, Budget Revenue reads `fact_budget` directly, both sliced by the same
`dim_date`/`dim_district` filter context).

`dim_date` is marked as the model's **Date Table** in Power BI (Modeling → Mark as
Date Table, using the `date` column) so all time-intelligence DAX functions
(`TOTALYTD`, `SAMEPERIODLASTYEAR`, `DATEADD`, etc.) work correctly. Fiscal year is
assumed equal to the calendar year (Jan–Dec) — there is nothing in the source data
suggesting NexWave uses an offset fiscal calendar; `fiscal_year`/`fiscal_quarter`
columns are included as placeholders in case that assumption needs revisiting.

## 4. Power Query (M) transformation steps

The Python script `scripts/03_build_star_schema.py` is the reference
implementation (it produces the exact CSVs in `data/clean/`), but if you'd rather
replicate the cleaning natively in Power BI's Power Query editor instead of
importing the pre-cleaned CSVs, use the M steps below per table. Load each raw
CSV first (`Get Data → Text/CSV`), then apply:

### `dim_district` (new table, not from a source file)

```m
let
    Source = #table(
        {"district"},
        {{"Center"}, {"Haifa"}, {"North"}, {"Jerusalem & South"}}
    )
in
    Source
```

### `dim_customer` (from `customers.csv`)

```m
let
    Source = Csv.Document(File.Contents("customers.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"customer_id", type text}, {"segment", type text},
        {"city", type text}, {"district", type text}
    }),
    Renamed = Table.RenameColumns(Typed, {{"district", "district_detail"}}),
    AddBudgetDistrict = Table.AddColumn(Renamed, "district", each
        if [district_detail] = "Jerusalem" or [district_detail] = "South"
        then "Jerusalem & South" else [district_detail], type text)
in
    AddBudgetDistrict
```

### `dim_dealer` (from `dealers.csv`, joined to customers' city→district map — §2.5)

```m
let
    Source = Csv.Document(File.Contents("dealers.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"dealer_code", type text}, {"dealer_name", type text},
        {"dealer_type", type text}, {"city", type text}
    }),
    // build the city -> district_detail lookup from dim_customer (loaded separately)
    CityDistrictMap = Table.Distinct(Table.SelectColumns(dim_customer, {"city", "district_detail"})),
    Merged = Table.NestedJoin(Typed, {"city"}, CityDistrictMap, {"city"}, "map", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Merged, "map", {"district_detail"}),
    FillOnline = Table.ReplaceValue(Expanded, null, "Online / N/A", Replacer.ReplaceValue, {"district_detail"}),
    AddBudgetDistrict = Table.AddColumn(FillOnline, "district", each
        if [district_detail] = "Jerusalem" or [district_detail] = "South"
        then "Jerusalem & South"
        else if [district_detail] = "Online / N/A" then "Online / N/A"
        else [district_detail], type text)
in
    AddBudgetDistrict
```

### `dim_plan` (from `price_plans.csv` — dedupe §2.2)

```m
let
    Source = Csv.Document(File.Contents("price_plans.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"plan_code", type text}, {"plan_name", type text},
        {"plan_family", type text}, {"monthly_list_price", Int64.Type}
    }),
    // push rows whose name contains "(legacy name)" to the bottom, then dedupe
    AddSortKey = Table.AddColumn(Typed, "_legacy_label", each Text.Contains([plan_name], "(legacy name)")),
    Sorted = Table.Sort(AddSortKey, {{"_legacy_label", Order.Ascending}}),
    Deduped = Table.Distinct(Sorted, {"plan_code"}),
    RemoveHelper = Table.RemoveColumns(Deduped, {"_legacy_label"}),
    AddLegacyFlag = Table.AddColumn(RemoveHelper, "is_legacy_plan", each Text.StartsWith([plan_code], "PLN-T"), type logical)
in
    AddLegacyFlag
```

### `dim_subscriber` (from `subscribers.csv` — normalize dealer_code §2.1, status/flags §2.6-2.7)

```m
let
    Source = Csv.Document(File.Contents("subscribers.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"subscriber_id", type text}, {"customer_id", type text},
        {"dealer_code", type text}, {"plan_code", type text},
        {"join_date", type date}, {"churn_date", type date}
    }),
    // normalize dealer_code: trim, uppercase, zero-pad numeric suffix to 2 digits
    TrimUpper = Table.TransformColumns(Typed, {{"dealer_code", each Text.Upper(Text.Trim(_)), type text}}),
    FixPrefix = Table.TransformColumns(TrimUpper, {{"dealer_code",
        each if Text.StartsWith(_, "DLR-") then _ else "DLR-" & Text.Trim(Text.Replace(_, "DLR", ""), {"-", "_", " "}),
        type text}}),
    PadSuffix = Table.TransformColumns(FixPrefix, {{"dealer_code",
        each "DLR-" & Text.PadStart(Text.AfterDelimiter(_, "DLR-"), 2, "0"), type text}}),
    AddStatus = Table.AddColumn(PadSuffix, "status", each if [churn_date] = null then "Active" else "Churned", type text),
    AddInWindow = Table.AddColumn(AddStatus, "in_billing_window", each
        [churn_date] = null or [churn_date] >= #date(2023, 7, 1), type logical),
    AddTenure = Table.AddColumn(AddInWindow, "tenure_days", each
        Duration.Days((if [churn_date] = null then #date(2025,12,31) else [churn_date]) - [join_date]), Int64.Type)
in
    AddTenure
```

### `dim_date` (new table — daily calendar spanning the billing range)

```m
let
    StartDate = #date(2023, 7, 1),
    EndDate = #date(2025, 12, 31),
    DayCount = Duration.Days(EndDate - StartDate) + 1,
    Dates = List.Dates(StartDate, DayCount, #duration(1, 0, 0, 0)),
    ToTable = Table.FromList(Dates, Splitter.SplitByNothing(), {"date"}),
    Typed = Table.TransformColumnTypes(ToTable, {{"date", type date}}),
    AddYear = Table.AddColumn(Typed, "year", each Date.Year([date]), Int64.Type),
    AddQuarter = Table.AddColumn(AddYear, "quarter", each "Q" & Text.From(Date.QuarterOfYear([date])), type text),
    AddYearQuarter = Table.AddColumn(AddQuarter, "year_quarter", each Text.From([year]) & "-" & [quarter], type text),
    AddMonthNum = Table.AddColumn(AddYearQuarter, "month_num", each Date.Month([date]), Int64.Type),
    AddMonthName = Table.AddColumn(AddMonthNum, "month_name", each Date.MonthName([date]), type text),
    AddYearMonth = Table.AddColumn(AddMonthName, "year_month", each Date.ToText([date], "yyyy-MM"), type text),
    AddYearMonthLabel = Table.AddColumn(AddYearMonth, "year_month_label", each Date.ToText([date], "MMM-yyyy"), type text),
    AddMonthStartFlag = Table.AddColumn(AddYearMonthLabel, "is_month_start", each Date.Day([date]) = 1, type logical),
    AddFiscalYear = Table.AddColumn(AddMonthStartFlag, "fiscal_year", each [year], Int64.Type)
in
    AddFiscalYear
```
*(Mark this table as the Date Table in Power BI Desktop: Table tools → Mark as Date Table → column `date`.)*

### `fact_billing` (from `monthly_billing.csv`)

```m
let
    Source = Csv.Document(File.Contents("monthly_billing.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"subscriber_id", type text}, {"billing_month", type text}, {"billed_amount", type number}
    }),
    AddDate = Table.AddColumn(Typed, "date", each Date.FromText([billing_month] & "-01"), type date),
    Final = Table.SelectColumns(AddDate, {"subscriber_id", "date", "billed_amount"})
in
    Final
```

### `fact_budget` (from `budget.csv` — unpivot wide months §2.4)

```m
let
    Source = Csv.Document(File.Contents("budget.csv"), [Delimiter=",", Encoding=65001]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Unpivoted = Table.UnpivotOtherColumns(Promoted, {"district", "line_item"}, "month_label", "budget_amount"),
    TypedAmount = Table.TransformColumnTypes(Unpivoted, {{"budget_amount", type number}}),
    AddDate = Table.AddColumn(TypedAmount, "date", each Date.FromText("1-" & [month_label]), type date),
    Final = Table.SelectColumns(AddDate, {"district", "date", "line_item", "budget_amount"})
in
    Final
```

## 5. Practical note on loading into Power BI

The simplest, lowest-risk path is to **import the already-cleaned CSVs from
`data/clean/`** directly (Get Data → Text/CSV, one per table) rather than
re-running the M transforms above from the raw files — the CSVs already embody
every decision in the memo and were validated for referential integrity
(script `scripts/03_build_star_schema.py` + inline checks: zero orphan keys across
all fact→dimension relationships). The M code above is provided so the
transformation logic is fully transparent and reproducible natively in Power
Query if preferred, or if the raw files need to be refreshed later.
