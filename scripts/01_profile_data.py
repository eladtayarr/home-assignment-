"""
Phase 1 — Data profiling and quality audit for NexWave Mobile dataset.
Reads the 6 raw CSVs and prints a structured profiling report used to
write docs/data_quality_memo.md.
"""
import pandas as pd
import numpy as np

pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)

RAW = "data/raw"

def hr(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

def profile_df(name, df):
    hr(f"PROFILE: {name}  (rows={len(df)}, cols={len(df.columns)})")
    print(df.dtypes)
    print("\n-- head --")
    print(df.head(3))
    print("\n-- null rate --")
    print((df.isna().mean() * 100).round(2).astype(str) + "%")
    print("\n-- cardinality (nunique) --")
    print(df.nunique())

# ---------- LOAD ----------
customers = pd.read_csv(f"{RAW}/customers.csv", dtype=str)
subscribers = pd.read_csv(f"{RAW}/subscribers.csv", dtype=str)
billing = pd.read_csv(f"{RAW}/monthly_billing.csv", dtype=str)
dealers = pd.read_csv(f"{RAW}/dealers.csv", dtype=str)
plans = pd.read_csv(f"{RAW}/price_plans.csv", dtype=str)
budget = pd.read_csv(f"{RAW}/budget.csv", dtype=str)

profile_df("customers", customers)
profile_df("subscribers", subscribers)
profile_df("dealers", dealers)
profile_df("price_plans", plans)
profile_df("budget", budget)
profile_df("monthly_billing", billing)

# ---------- DUPLICATE / KEY CHECKS ----------
hr("KEY UNIQUENESS CHECKS")
print("customers.customer_id duplicates:", customers.customer_id.duplicated().sum())
print("subscribers.subscriber_id duplicates:", subscribers.subscriber_id.duplicated().sum())
print("dealers.dealer_code duplicates (raw):", dealers.dealer_code.duplicated().sum())
print("price_plans.plan_code duplicates (raw):", plans.plan_code.duplicated().sum())
print("monthly_billing (subscriber_id, billing_month) duplicates:",
      billing.duplicated(subset=["subscriber_id", "billing_month"]).sum())

hr("CUSTOMERS: segment / city / district value counts")
print(customers.segment.value_counts(dropna=False))
print(customers.district.value_counts(dropna=False))
print("distinct cities:", customers.city.nunique())

hr("DEALERS raw table (full, small)")
print(dealers.to_string())

hr("PRICE_PLANS raw table (full, small)")
print(plans.to_string())

hr("BUDGET raw table (full, small)")
print(budget.to_string())

# ---------- DEALER_CODE FORMATTING MISMATCH ----------
hr("DEALER_CODE FORMAT: subscribers.csv vs dealers.csv")
print("subscribers.dealer_code sample raw values:")
print(subscribers.dealer_code.value_counts(dropna=False).head(30))
print("\ndealers.dealer_code raw values:")
print(dealers.dealer_code.tolist())

def norm_dealer_code(x):
    if pd.isna(x):
        return x
    s = str(x).strip().upper()
    # normalize DLR-1 -> DLR-01 style (zero-pad numeric suffix to 2 digits)
    if s.startswith("DLR-") or s.startswith("DLR"):
        s = s.replace("DLR_", "DLR-").replace("DLR ", "DLR-")
        if not s.startswith("DLR-"):
            s = "DLR-" + s[3:].lstrip("-_ ")
        suffix = s[4:]
        if suffix.isdigit():
            suffix = suffix.zfill(2)
        s = "DLR-" + suffix
    return s

sub_codes_raw = subscribers.dealer_code.dropna().unique()
sub_codes_norm = pd.Series(sub_codes_raw).map(norm_dealer_code)
dealer_codes_norm = dealers.dealer_code.map(norm_dealer_code)

print("\nUnique raw subscriber dealer_code count:", len(sub_codes_raw))
print("Unique normalized subscriber dealer_code count:", sub_codes_norm.nunique())
print("Unique normalized dealer table dealer_code count:", dealer_codes_norm.nunique())

unmatched_after_norm = set(sub_codes_norm) - set(dealer_codes_norm)
print("\nNormalized subscriber codes with NO match in dealers table:", unmatched_after_norm)

raw_to_norm = pd.DataFrame({"raw": sub_codes_raw, "norm": sub_codes_norm})
print("\nExamples of raw variants mapping to same normalized code (formatting issue evidence):")
grp = raw_to_norm.groupby("norm")["raw"].apply(lambda s: sorted(set(s)))
print(grp[grp.apply(len) > 1])

# ---------- PLAN_CODE DUPLICATES / CONFLICTS ----------
hr("PRICE_PLANS: duplicate / conflicting plan_code")
dup_mask = plans.duplicated(subset=["plan_code"], keep=False)
print(plans[dup_mask].sort_values("plan_code"))
print("\nplan_code normalized (strip/upper) duplicate check:")
plans["plan_code_norm"] = plans.plan_code.str.strip().str.upper()
dup_norm = plans.duplicated(subset=["plan_code_norm"], keep=False)
print(plans[dup_norm].sort_values("plan_code_norm"))

# ---------- DISTRICT RECONCILIATION ----------
hr("DISTRICT RECONCILIATION: budget.csv vs customers.csv/dealers.csv")
print("budget districts:", sorted(budget.district.unique()))
print("customers districts:", sorted(customers.district.dropna().unique()))
print("dealers - no district column" if "district" not in dealers.columns else sorted(dealers.district.unique()))

budget_districts = set(budget.district.unique())
customer_districts = set(customers.district.dropna().unique())
print("\nIn budget but not customers:", budget_districts - customer_districts)
print("In customers but not budget:", customer_districts - budget_districts)

hr("BUDGET: line_item values")
print(budget.line_item.value_counts())

# ---------- BILLING INTEGRITY ----------
hr("BILLING INTEGRITY CHECKS")
billing["billed_amount_f"] = pd.to_numeric(billing.billed_amount, errors="coerce")
print("Non-numeric billed_amount rows:", billing.billed_amount_f.isna().sum() - billing.billed_amount.isna().sum())
print("Negative billed_amount rows:", (billing.billed_amount_f < 0).sum())
print("Zero billed_amount rows:", (billing.billed_amount_f == 0).sum())
print("billed_amount describe:\n", billing.billed_amount_f.describe())

billing["billing_month_dt"] = pd.to_datetime(billing.billing_month, format="%Y-%m", errors="coerce")
print("\nbilling_month range:", billing.billing_month_dt.min(), "to", billing.billing_month_dt.max())
print("Unparseable billing_month rows:", billing.billing_month_dt.isna().sum())

# orphan billing: subscriber_id not in subscribers.csv
valid_subs = set(subscribers.subscriber_id)
orphan_billing = billing[~billing.subscriber_id.isin(valid_subs)]
print("\nBilling rows with subscriber_id NOT in subscribers.csv:", len(orphan_billing))
print(orphan_billing.subscriber_id.unique()[:20])

# billing after churn_date
subscribers["join_date_dt"] = pd.to_datetime(subscribers.join_date, format="%m/%d/%Y", errors="coerce")
subscribers["churn_date_dt"] = pd.to_datetime(subscribers.churn_date, format="%m/%d/%Y", errors="coerce")
print("\njoin_date unparseable:", subscribers.join_date_dt.isna().sum(), "of", len(subscribers))
print("churn_date populated:", subscribers.churn_date_dt.notna().sum(), "of", len(subscribers),
      f"({subscribers.churn_date_dt.notna().mean()*100:.1f}%)")

merged = billing.merge(subscribers[["subscriber_id", "churn_date_dt", "join_date_dt"]], on="subscriber_id", how="left")
merged["billing_month_end"] = merged.billing_month_dt + pd.offsets.MonthEnd(0)
after_churn = merged[merged.churn_date_dt.notna() & (merged.billing_month_end > merged.churn_date_dt)]
print("\nBilling rows AFTER churn_date:", len(after_churn), f"({len(after_churn)/len(merged)*100:.3f}% of billing rows)")
print("Distinct subscribers affected:", after_churn.subscriber_id.nunique())
print(after_churn[["subscriber_id", "billing_month", "churn_date_dt", "billed_amount"]].head(10))

# billing before join_date
before_join = merged[merged.join_date_dt.notna() & (merged.billing_month_dt < merged.join_date_dt.values.astype("datetime64[M]"))]
print("\nBilling rows BEFORE join_date (month before join month):", len(before_join))

# subscribers with no billing at all
subs_with_billing = set(billing.subscriber_id.unique())
subs_no_billing = subscribers[~subscribers.subscriber_id.isin(subs_with_billing)]
print("\nSubscribers with ZERO billing rows:", len(subs_no_billing), "of", len(subscribers))
print(subs_no_billing[["subscriber_id", "join_date", "churn_date"]].head(10))

# ---------- CUSTOMER <-> SUBSCRIBER referential check ----------
hr("SUBSCRIBERS -> CUSTOMERS referential check")
valid_customers = set(customers.customer_id)
orphan_subs = subscribers[~subscribers.customer_id.isin(valid_customers)]
print("Subscribers with customer_id not in customers.csv:", len(orphan_subs))

# subscribers -> plan_code referential
valid_plans = set(plans.plan_code)
orphan_plan_ref = subscribers[~subscribers.plan_code.isin(valid_plans)]
print("Subscribers with plan_code not in price_plans.csv:", len(orphan_plan_ref))
if len(orphan_plan_ref):
    print(orphan_plan_ref.plan_code.value_counts())

# subscribers -> dealer_code referential (raw, before normalization)
valid_dealers_raw = set(dealers.dealer_code)
orphan_dealer_ref_raw = subscribers[~subscribers.dealer_code.isin(valid_dealers_raw)]
print("\nSubscribers with dealer_code NOT matching dealers.csv RAW:", len(orphan_dealer_ref_raw),
      f"({len(orphan_dealer_ref_raw)/len(subscribers)*100:.1f}%)")

orphan_dealer_ref_norm = subscribers[~subscribers.dealer_code.map(norm_dealer_code).isin(dealer_codes_norm)]
print("Subscribers with dealer_code NOT matching dealers.csv AFTER normalization:", len(orphan_dealer_ref_norm))

# multiple subscribers per customer
hr("CUSTOMER -> SUBSCRIBER cardinality")
subs_per_cust = subscribers.groupby("customer_id").size()
print(subs_per_cust.value_counts().sort_index())
print("Max subscribers for one customer:", subs_per_cust.max())
print("Customers with >1 subscriber:", (subs_per_cust > 1).sum(), "of", customers.customer_id.nunique())

print("\nDONE")
