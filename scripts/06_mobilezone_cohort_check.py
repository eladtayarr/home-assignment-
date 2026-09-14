"""Phase 4 ad hoc: confirm MobileZone's H2-2025 churn spike traces to its H1-2025
acquisition surge cohort (low tenure at churn, high cohort churn speed)."""
import pandas as pd

C = "data/clean"
dim_subscriber = pd.read_csv(f"{C}/dim_subscriber.csv", parse_dates=["join_date", "churn_date"])
dim_dealer = pd.read_csv(f"{C}/dim_dealer.csv")
sub = dim_subscriber.merge(dim_dealer[["dealer_code", "dealer_name"]], on="dealer_code")

mz = sub[sub.dealer_name == "MobileZone"].copy()
mz_churned_h2 = mz[(mz.churn_date >= "2025-07-01") & (mz.churn_date <= "2025-12-31")]

print("MobileZone subscribers ever:", len(mz), f"({len(mz)/len(sub)*100:.1f}% of company base)")
print("MobileZone subs churned in H2 2025:", len(mz_churned_h2))
print("\nTenure (days) at churn, MobileZone H2-2025 churners:")
print(mz_churned_h2.tenure_days.describe())
print("\nCompany-wide tenure (days) at churn, ALL churned subscribers (for comparison):")
print(dim_subscriber.dropna(subset=["churn_date"]).tenure_days.describe())

print("\nJoin-quarter distribution of MobileZone's H2-2025 churners (77% from 2025 Q1/Q2 surge):")
print(mz_churned_h2.join_date.dt.to_period("Q").value_counts().sort_index())

mz_h1_2025_cohort = mz[(mz.join_date >= "2025-01-01") & (mz.join_date <= "2025-06-30")]
churn_rate_of_cohort = mz_h1_2025_cohort.churn_date.notna().mean() * 100
print(f"\nMobileZone H1-2025 acquisition cohort size: {len(mz_h1_2025_cohort)}")
print(f"% of that cohort already churned by end of 2025: {churn_rate_of_cohort:.1f}%")
