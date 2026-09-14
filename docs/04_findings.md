# Phase 4 — Exploratory Findings

## The headline finding

**A single franchise dealer's low-quality H1‑2025 acquisition surge is driving a
company-wide churn increase that is now visibly eroding the 2025 revenue budget in
Q4 — while headline revenue and subscriber counts still look fine month to month.**
This is exactly the "looks fine on the surface, something feels off" pattern
management described, and it traces to one identifiable, fixable cause.

### The chain of evidence

**1. Company-wide monthly churn rate has stepped up since mid‑2025.**
From launch (2023‑07) through June 2025, the monthly churn rate was flat and stable
around **1.8–2.0%** (24 months of history, barely moving). Starting July 2025 it
climbs steadily: 2.11% (Jul) → 2.41% (Aug) → 2.23% (Sep) → **2.59% (Oct, the
period high)** → 2.41% (Nov) → 2.13% (Dec). The trailing-3-month average rose from
1.82% in January to 2.38% in December — **a ~30% relative increase**, and a clear
break from 24 months of stability, not noise.

**2. It is not broad-based — it is almost entirely one dealer.**
Splitting the H1‑2025 vs. H2‑2025 average monthly churn rate by dealer:

| Dealer | H1 2025 avg | H2 2025 avg | Change |
|---|---|---|---|
| **MobileZone** | **1.98%** | **4.47%** | **+2.48 pp (+125%)** |
| GalaxyCom | 1.56% | 1.77% | +0.21 pp |
| PhoneHub | 1.73% | 1.90% | +0.16 pp |
| MobileNow | 1.72% | 1.76% | +0.04 pp |
| TopCell | 1.82% | 1.85% | +0.03 pp |
| SmartShop | 1.85% | 1.87% | +0.02 pp |
| NexWave Store Tel Aviv | 1.81% | 1.72% | −0.09 pp |
| NexWave Online | 1.90% | 1.80% | −0.10 pp |
| NexWave Store Haifa | 1.98% | 1.81% | −0.17 pp |
| CellFix | 1.92% | 1.74% | −0.17 pp |

Nine of ten dealers moved by ±0.2pp — normal noise. **MobileZone moved by 2.5
percentage points** — more than 10x any other dealer, and by itself large enough to
move the entire company average given MobileZone is **18.5% of the total
subscriber base** (9,466 of 51,143 subscribers ever acquired).

**3. Segment/district/plan-family splits show no comparable concentration** — churn
rose everywhere by roughly similar, smaller amounts (e.g. Seg A +0.36pp, Seg D
+0.62pp; all districts +0.29 to +0.52pp) consistent with simply absorbing
MobileZone's book, not a second independent cause. Legacy vs. core plan codes show
essentially identical churn behavior (29.3% vs 29.8% cumulative) — the plan
sprawl flagged in the data quality memo is a real governance item but **not** a
driver of this churn pattern.

**4. The root cause traces to a specific acquisition anomaly.**
In H1 2025, MobileZone's share of *all new company subscribers* jumped to
**~40%** (vs. a normal ~15–19% in line with its base share) — then collapsed to
**~13–15%** starting exactly in July 2025, the same month its churn rate started
climbing. Of the 1,701 MobileZone subscribers who churned in H2 2025, **77% had
joined in Q1 or Q2 2025** — i.e. they are the surge cohort itself, not
longer-tenured customers. Their median tenure at churn was **~184 days (~6
months)**, well under the company-wide churned-subscriber median of 335 days.
**43% of the entire H1‑2025 MobileZone acquisition cohort (3,508 subscribers) had
already churned by year-end** — a churn speed far outside normal telco cohort
behavior, consistent with a subsidy-driven, quota-driven, or otherwise low-intent
sign-up push rather than durable new business.

**5. Financial impact — this is where "looks fine on the surface" comes from.**
Total revenue and net subscriber adds were positive **every single month** of
2025 — nothing about the top-line trend alone would prompt concern. But look
underneath:
- Revenue MoM growth decelerated steadily through the second half of the year:
  **+3.4% in June → +1.9% in September → +1.2% in December.**
- The 2025 revenue budget (by district) was being **beaten** through September
  (cumulative variance peaked at **+$24.4K** in September) and then **flipped to a
  miss**: −$11.1K (Oct) → −$19.2K (Nov) → **−$80.5K cumulative by December** —
  entirely a Q4 phenomenon, coinciding exactly with the churn acceleration.

## What's interesting but NOT the actionable story (and why)

To be explicit about what was investigated and set aside:
- **Plan catalog sprawl** (25 near-duplicate legacy plan codes, 20% of active
  subscribers) — real and worth cleaning up, but churn behavior is identical
  between legacy and core plans, so it isn't contributing to this problem.
- **Segment ARPU differences** (Seg A ~$904 lifetime vs. Seg D ~$763) — expected
  and structural (higher segments simply pay more), not a recent shift.
- **Revenue concentration in Smart/Unlimited plan families** (67% of revenue) —
  normal mix for a mobile operator, not an anomaly.
- **District-level churn/ARPU variation** — differences exist (Jerusalem ARPU
  slightly lower, etc.) but are small and don't show a distinct recent break the
  way the dealer split does.

## Recommendation

1. **Immediate:** investigate MobileZone's H1‑2025 sales practices — was there a
   promotion, subsidized device/SIM deal, or an internal sales-quota push that
   incentivized volume over quality? Pull cancellation-reason data (not present in
   this dataset) for the H1‑2025 cohort specifically.
2. **Contain:** consider a temporary cap or enhanced monitoring on new activations
   through MobileZone until the cause is confirmed and fixed — the H1‑2025 cohort
   is still churning (31 new churns from that cohort recorded even in Q3, and the
   dealer's churn rate, while off its October peak, was still 3.75% in December
   vs. ~1.8% normal).
3. **Structural fix:** dealer performance should be tracked on **acquisition
   quality (e.g. a 90/180‑day retention rate by dealer), not gross adds alone** —
   gross-adds-only reporting is exactly why this went unnoticed for two quarters
   while the dealer looked like the company's top performer. This becomes a
   standing dashboard measure, not a one-time investigation.
4. **Forecast:** flag 2025 year-end and 2026 budget assumptions for revision if
   MobileZone's book doesn't stabilize — the current trajectory implies the churn
   drag continues into Q1 2026.

## Recap: which pandas outputs support this

- `scripts/04_exploratory_analysis.py` §1–2, §5: overall revenue/churn trend and
  budget variance
- `scripts/05_churn_driver_analysis.py`: churn-rate breakdown by dealer/segment/
  district/plan family, H1-vs-H2 deltas, dealer acquisition share shift
- Ad hoc MobileZone cohort check (tenure-at-churn, join-quarter distribution,
  H1‑2025 cohort churn rate) — see conversation / can be re-run on request
