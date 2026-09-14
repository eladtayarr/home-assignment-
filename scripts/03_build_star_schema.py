"""
Phase 2 — Build the star schema for Power BI from the raw CSVs.

Applies every decision from docs/01_data_quality_memo.md and writes clean,
load-ready CSVs to data/clean/:

  dim_district.csv    - 4 rows, the budget-comparable district grain (PK: district)
  dim_customer.csv    - 1 row / customer, incl. district (FK->dim_district) and
                         district_detail (granular 5-way, attribute only)
  dim_dealer.csv       - 1 row / dealer, incl. district (FK->dim_district) and
                         district_detail
  dim_plan.csv         - 1 row / plan_code (deduped), incl. plan_family
  dim_subscriber.csv   - 1 row / subscriber, incl. FKs to customer/dealer/plan,
                         join_date/churn_date, status, in_billing_window flag
  dim_date.csv          - daily calendar 2023-07-01 -> 2025-12-31
  fact_billing.csv     - grain: subscriber_id x month (first-of-month date)
  fact_budget.csv      - grain: district x month (first-of-month date), 2025 only
"""
import pandas as pd
import numpy as np

RAW = "data/raw"
OUT = "data/clean"

# ---------------------------------------------------------------------------
# 1. dim_district  (§2.4, §2.5 of the memo)
# ---------------------------------------------------------------------------
# Budget-comparable grain: Center, Haifa, North, "Jerusalem & South"
dim_district = pd.DataFrame({
    "district": ["Center", "Haifa", "North", "Jerusalem & South"],
})
dim_district.to_csv(f"{OUT}/dim_district.csv", index=False)

# bridge used to derive district / district_detail on customer & dealer tables
BUDGET_DISTRICT_MAP = {
    "Center": "Center",
    "Haifa": "Haifa",
    "North": "North",
    "Jerusalem": "Jerusalem & South",
    "South": "Jerusalem & South",
}

# ---------------------------------------------------------------------------
# 2. dim_customer
# ---------------------------------------------------------------------------
customers = pd.read_csv(f"{RAW}/customers.csv", dtype=str)
customers = customers.rename(columns={"district": "district_detail"})
customers["district"] = customers.district_detail.map(BUDGET_DISTRICT_MAP)
customers = customers[["customer_id", "segment", "city", "district_detail", "district"]]
customers.to_csv(f"{OUT}/dim_customer.csv", index=False)

# ---------------------------------------------------------------------------
# 3. dim_dealer  (§2.5 — derive district from city via customers' city->district map)
# ---------------------------------------------------------------------------
dealers = pd.read_csv(f"{RAW}/dealers.csv", dtype=str)
city_to_district_detail = (
    pd.read_csv(f"{RAW}/customers.csv", dtype=str)
    .drop_duplicates(subset=["city"])
    .set_index("city")["district"]
    .to_dict()
)
dealers["district_detail"] = dealers.city.map(city_to_district_detail).fillna("Online / N/A")
dealers["district"] = dealers.district_detail.map(BUDGET_DISTRICT_MAP).fillna("Online / N/A")
dealers = dealers[["dealer_code", "dealer_name", "dealer_type", "city", "district_detail", "district"]]
dealers.to_csv(f"{OUT}/dim_dealer.csv", index=False)

# ---------------------------------------------------------------------------
# 4. dim_plan  (§2.2 — drop duplicate PLN-S100 legacy-name row)
# ---------------------------------------------------------------------------
plans = pd.read_csv(f"{RAW}/price_plans.csv", dtype=str)
plans["monthly_list_price"] = pd.to_numeric(plans.monthly_list_price)
plans["is_legacy_plan"] = plans.plan_code.str.startswith("PLN-T")
# keep the non-"(legacy name)" labeled row when a plan_code is duplicated
plans["_is_legacy_label"] = plans.plan_name.str.contains(r"\(legacy name\)", regex=True)
plans = plans.sort_values("_is_legacy_label").drop_duplicates(subset=["plan_code"], keep="first")
plans = plans.drop(columns="_is_legacy_label").sort_values("plan_code")
plans.to_csv(f"{OUT}/dim_plan.csv", index=False)

# ---------------------------------------------------------------------------
# 5. dim_subscriber  (§2.1 — normalize dealer_code; §2.6/§2.7 assumptions)
# ---------------------------------------------------------------------------
subscribers = pd.read_csv(f"{RAW}/subscribers.csv", dtype=str)

def norm_dealer_code(x):
    if pd.isna(x):
        return x
    s = str(x).strip().upper()
    if not s.startswith("DLR-"):
        s = "DLR-" + s.replace("DLR", "").lstrip("-_ ")
    suffix = s[4:]
    if suffix.isdigit():
        suffix = suffix.zfill(2)
    return "DLR-" + suffix

subscribers["dealer_code"] = subscribers.dealer_code.map(norm_dealer_code)
subscribers["join_date"] = pd.to_datetime(subscribers.join_date, format="%m/%d/%Y")
subscribers["churn_date"] = pd.to_datetime(subscribers.churn_date, format="%m/%d/%Y", errors="coerce")
subscribers["status"] = np.where(subscribers.churn_date.isna(), "Active", "Churned")
BILLING_WINDOW_START = pd.Timestamp("2023-07-01")
subscribers["in_billing_window"] = subscribers.churn_date.isna() | (subscribers.churn_date >= BILLING_WINDOW_START)
subscribers["tenure_days"] = (subscribers.churn_date.fillna(pd.Timestamp("2025-12-31")) - subscribers.join_date).dt.days

subscribers = subscribers[[
    "subscriber_id", "customer_id", "dealer_code", "plan_code",
    "join_date", "churn_date", "status", "in_billing_window", "tenure_days",
]]
subscribers.to_csv(f"{OUT}/dim_subscriber.csv", index=False)

# ---------------------------------------------------------------------------
# 6. dim_date  (daily calendar, full monthly_billing range)
# ---------------------------------------------------------------------------
dates = pd.date_range("2023-07-01", "2025-12-31", freq="D")
dim_date = pd.DataFrame({"date": dates})
dim_date["year"] = dim_date.date.dt.year
dim_date["quarter"] = "Q" + dim_date.date.dt.quarter.astype(str)
dim_date["year_quarter"] = dim_date.year.astype(str) + "-" + dim_date.quarter
dim_date["month_num"] = dim_date.date.dt.month
dim_date["month_name"] = dim_date.date.dt.strftime("%B")
dim_date["month_short"] = dim_date.date.dt.strftime("%b")
dim_date["year_month"] = dim_date.date.dt.strftime("%Y-%m")
dim_date["year_month_label"] = dim_date.date.dt.strftime("%b-%Y")
dim_date["day_of_month"] = dim_date.date.dt.day
dim_date["is_month_start"] = dim_date.date.dt.is_month_start
dim_date["is_month_end"] = dim_date.date.dt.is_month_end
# fiscal year assumed = calendar year (Jan-Dec); no evidence in source data of a
# different fiscal calendar, documented as an assumption in docs/02_data_model.md
dim_date["fiscal_year"] = dim_date.year
dim_date["fiscal_quarter"] = dim_date.quarter
dim_date.to_csv(f"{OUT}/dim_date.csv", index=False)

# ---------------------------------------------------------------------------
# 7. fact_billing  (grain: subscriber_id x month)
# ---------------------------------------------------------------------------
billing = pd.read_csv(f"{RAW}/monthly_billing.csv", dtype=str)
billing["billed_amount"] = pd.to_numeric(billing.billed_amount)
billing["date"] = pd.to_datetime(billing.billing_month, format="%Y-%m")
fact_billing = billing[["subscriber_id", "date", "billed_amount"]].sort_values(["date", "subscriber_id"])
fact_billing.to_csv(f"{OUT}/fact_billing.csv", index=False)

# ---------------------------------------------------------------------------
# 8. fact_budget  (unpivot wide months -> long; grain: district x month)
# ---------------------------------------------------------------------------
budget = pd.read_csv(f"{RAW}/budget.csv", dtype=str)
month_cols = [c for c in budget.columns if c not in ("district", "line_item")]
fact_budget = budget.melt(id_vars=["district", "line_item"], value_vars=month_cols,
                           var_name="month_label", value_name="budget_amount")
fact_budget["budget_amount"] = pd.to_numeric(fact_budget.budget_amount)
fact_budget["date"] = pd.to_datetime(fact_budget.month_label, format="%b-%Y")
fact_budget = fact_budget[["district", "date", "line_item", "budget_amount"]].sort_values(["date", "district"])
fact_budget.to_csv(f"{OUT}/fact_budget.csv", index=False)

# ---------------------------------------------------------------------------
print("Star schema written to data/clean/:")
for f in ["dim_district", "dim_customer", "dim_dealer", "dim_plan", "dim_subscriber",
          "dim_date", "fact_billing", "fact_budget"]:
    df = pd.read_csv(f"{OUT}/{f}.csv")
    print(f"  {f:16s} rows={len(df):>8}  cols={list(df.columns)}")
