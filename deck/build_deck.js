const pptxgen = require("pptxgenjs");
const fs = require("fs");

const DATA_DIR = "/tmp/claude-0/-home-user-home-assignment-/a7921034-e6ed-5b0c-adb9-223511b76b84/scratchpad/deck_data";
const load = (f) => JSON.parse(fs.readFileSync(`${DATA_DIR}/${f}`, "utf8"));

const churnTrend = load("churn_trend.json");
const revVsBudget = load("revenue_vs_budget.json");
const cumVariance = load("cum_variance.json");
const dealerChurn = load("dealer_churn.json");
const cohortChurn = load("cohort_churn.json");
const mzShare = load("mz_share_trend.json");
const revTrend = load("revenue_trend.json");

// ---- palette: "Signal in the Noise" -- muted slate/navy base, one sharp warning red for the MobileZone thread ----
const NAVY = "1E2761";
const ICE = "CADCFC";
const SLATE = "5B6B8C";
const PAPER = "F7F8FB";
const INK = "1B1F2A";
const MUTE = "8993A8";
const WARN = "C0392B"; // reserved exclusively for MobileZone / at-risk callouts
const GOOD = "1F7A5C";
const WHITE = "FFFFFF";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5"
pres.author = "Elad";
pres.company = "NexWave Mobile";
pres.title = "NexWave Mobile — Q4 2025 Business Health Review";

const FONT = "Calibri";
const HEAD_FONT = "Cambria";

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  return s;
}

function kicker(slide, text, opts = {}) {
  slide.addText(text.toUpperCase(), {
    x: 0.6, y: opts.y ?? 0.45, w: 9, h: 0.35,
    fontFace: FONT, fontSize: 12, bold: true, color: opts.color ?? SLATE,
    charSpacing: 2, isTextBox: true, margin: 0,
  });
}
function title(slide, text, opts = {}) {
  slide.addText(text, {
    x: 0.6, y: opts.y ?? 0.78, w: opts.w ?? 11.8, h: opts.h ?? 0.9,
    fontFace: HEAD_FONT, fontSize: opts.size ?? 32, bold: true,
    color: opts.color ?? INK, isTextBox: true, margin: 0,
  });
}
function pageNum(slide, n) {
  slide.addText(`${n} / 10`, {
    x: 12.5, y: 7.05, w: 0.7, h: 0.35, fontFace: FONT, fontSize: 10,
    color: MUTE, align: "right", isTextBox: true, margin: 0,
  });
}

// =====================================================================
// SLIDE 1 — Title
// =====================================================================
{
  const s = darkSlide();
  s.addText("NEXWAVE MOBILE", {
    x: 0.9, y: 1.5, w: 8, h: 0.4, fontFace: FONT, fontSize: 14, bold: true,
    color: ICE, charSpacing: 3, isTextBox: true, margin: 0,
  });
  s.addText("The numbers look fine.\nHere's what's underneath.", {
    x: 0.9, y: 2.0, w: 10.8, h: 2.3, fontFace: HEAD_FONT, fontSize: 42, bold: true,
    color: WHITE, isTextBox: true, margin: 0, lineSpacingMultiple: 1.08,
  });
  s.addText("Q4 2025 Business Health Review — Revenue, Churn & Budget Performance", {
    x: 0.9, y: 4.35, w: 10, h: 0.5, fontFace: FONT, fontSize: 17, color: ICE,
    isTextBox: true, margin: 0,
  });
  s.addText("Prepared by Elad  ·  Data Analyst home assignment  ·  NexWave Mobile", {
    x: 0.9, y: 6.6, w: 10, h: 0.4, fontFace: FONT, fontSize: 12, color: SLATE,
    isTextBox: true, margin: 0,
  });
  // simple motif: a thin rising dot-path suggestion using shapes (churn line motif), no accent stripes
  const pts = [0.15, 0.14, 0.16, 0.15, 0.17, 0.19, 0.24, 0.28, 0.30];
  const chartX = 9.6, chartY = 1.6, chartW = 3.0, chartH = 1.1;
  s.addChart(pres.ChartType.line, [{
    name: "signal",
    labels: pts.map((_, i) => `${i}`),
    values: pts,
  }], {
    x: chartX, y: chartY, w: chartW, h: chartH,
    chartColors: [WARN], lineSize: 3, lineDataSymbol: "none",
    showLegend: false, showTitle: false, showValue: false,
    catAxisHidden: true, valAxisHidden: true,
    catGridLine: { style: "none" }, valGridLine: { style: "none" },
    chartArea: { fill: { color: NAVY } }, plotArea: { fill: { color: NAVY } },
  });
}

// =====================================================================
// SLIDE 2 — The question we were asked
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "The brief");
  title(s, "“The numbers look fine on the surface,\nbut something feels off lately.”", { h: 1.5 });
  s.addText("— NexWave Mobile management", {
    x: 0.6, y: 2.7, w: 8, h: 0.4, fontFace: FONT, italic: true, fontSize: 14, color: MUTE,
    isTextBox: true, margin: 0,
  });

  const cards = [
    { h: "Revenue", v: "up every month\nin 2025" },
    { h: "Net adds", v: "positive every\nmonth in 2025" },
    { h: "Subscriber base", v: "at an all-time\nhigh, Dec 2025" },
  ];
  let cx = 0.6;
  cards.forEach((c) => {
    s.addShape(pres.ShapeType.roundRect, {
      x: cx, y: 3.5, w: 3.7, h: 2.1, rectRadius: 0.08,
      fill: { color: WHITE }, line: { color: "E3E7EF", width: 1 },
      shadow: { type: "outer", color: "1B1F2A", opacity: 0.12, blur: 8, offset: 3, angle: 90 },
    });
    s.addText(c.h.toUpperCase(), {
      x: cx + 0.3, y: 3.75, w: 3.1, h: 0.4, fontFace: FONT, fontSize: 11, bold: true,
      color: SLATE, charSpacing: 1.5, isTextBox: true, margin: 0,
    });
    s.addText(c.v, {
      x: cx + 0.3, y: 4.2, w: 3.1, h: 1.2, fontFace: HEAD_FONT, fontSize: 20, bold: true,
      color: GOOD, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1,
    });
    cx += 4.0;
  });

  s.addText("So on paper, 2025 looks like a strong year. This deck is about what that topline view is hiding — and why it matters before it gets bigger.", {
    x: 0.6, y: 5.85, w: 12, h: 0.9, fontFace: FONT, fontSize: 15, color: INK,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 2);
}

// =====================================================================
// SLIDE 3 — Revenue trend (looks fine)
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "What the topline shows");
  title(s, "Revenue has grown every month since launch");

  s.addChart(pres.ChartType.line,
    [
      { name: "Monthly revenue (k)", labels: revTrend.labels, values: revTrend.revenue_k },
    ],
    {
      x: 0.6, y: 2.0, w: 12.1, h: 4.2,
      chartColors: [NAVY],
      lineSize: 2.5, lineDataSymbol: "none",
      showTitle: true, title: "Total billed revenue, ₪k per month (Jul-2023 → Dec-2025)",
      titleFontSize: 13, titleColor: INK, titleFontFace: FONT,
      showLegend: false,
      showValue: false,
      catAxisLabelColor: MUTE, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 8, valAxisLabelFontSize: 9,
      catAxisOrientation: "minMax",
      valGridLine: { color: "E3E7EF", size: 1 },
      catGridLine: { style: "none" },
      catAxisLabelRotate: 45,
    }
  );
  s.addText("30 consecutive months of growth. No red flags here — which is exactly why this needs a second look.", {
    x: 0.6, y: 6.45, w: 12, h: 0.5, fontFace: FONT, fontSize: 14, italic: true, color: MUTE,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 3);
}

// =====================================================================
// SLIDE 4 — Churn rate breaking trend
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "Where it breaks down", { color: WARN });
  title(s, "Underneath: monthly churn has stepped up ~30%");

  s.addChart(pres.ChartType.line,
    [
      { name: "Monthly churn rate %", labels: churnTrend.labels, values: churnTrend.churn_rate },
      { name: "Trailing 3-month avg", labels: churnTrend.labels, values: churnTrend.trail3 },
    ],
    {
      x: 0.6, y: 1.9, w: 12.1, h: 4.3,
      chartColors: [ "C9CEDC", WARN ],
      lineSize: [1.5, 3],
      lineDataSymbol: "none",
      showTitle: true, title: "Monthly churn rate, % of prior-month base (Jul-2023 → Dec-2025)",
      titleFontSize: 13, titleColor: INK, titleFontFace: FONT,
      showLegend: true, legendPos: "b", legendFontSize: 10,
      showValue: false,
      catAxisLabelColor: MUTE, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 8, valAxisLabelFontSize: 9,
      valGridLine: { color: "E3E7EF", size: 1 },
      catGridLine: { style: "none" },
      catAxisLabelRotate: 45,
      valAxisTitle: "%", showValAxisTitle: true, valAxisTitleFontSize: 10,
    }
  );
  s.addText([
    { text: "1.8% → 2.6%", options: { bold: true, color: WARN, fontSize: 16 } },
    { text: "  —  stable 2023–2024 baseline to the October 2025 peak, a ~30% relative increase.", options: { color: INK, fontSize: 14 } },
  ], {
    x: 0.6, y: 6.45, w: 12.1, h: 0.5, fontFace: FONT, isTextBox: true, margin: 0,
  });
  pageNum(s, 4);
}

// =====================================================================
// SLIDE 5 — Isolating the cause: one dealer
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "Isolating the cause", { color: WARN });
  title(s, "It isn't broad-based — it's one dealer.");

  const dealerColors = dealerChurn.dealers.map(d => d === "MobileZone" ? WARN : "C9CEDC");
  s.addChart(pres.ChartType.bar,
    [
      { name: "H1 2025 avg churn %", labels: dealerChurn.dealers, values: dealerChurn.h1 },
      { name: "H2 2025 avg churn %", labels: dealerChurn.dealers, values: dealerChurn.h2 },
    ],
    {
      x: 0.6, y: 1.9, w: 12.1, h: 4.5,
      barDir: "col",
      chartColors: ["A9B3C9", WARN],
      showTitle: true, title: "Average monthly churn rate by dealer: H1 2025 vs H2 2025",
      titleFontSize: 13, titleColor: INK, titleFontFace: FONT,
      showLegend: true, legendPos: "b", legendFontSize: 10,
      showValue: false,
      catAxisLabelColor: INK, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 9,
      catAxisLabelRotate: 25,
      valGridLine: { color: "E3E7EF", size: 1 },
      catGridLine: { style: "none" },
      valAxisTitle: "%", showValAxisTitle: true, valAxisTitleFontSize: 10,
    }
  );
  s.addText("MobileZone: +2.5 points (H1→H2) — more than 10× any other dealer's shift, on a dealer that is 18.5% of the subscriber base.", {
    x: 0.6, y: 6.55, w: 12, h: 0.5, fontFace: FONT, fontSize: 13.5, bold: true, color: WARN,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 5);
}

// =====================================================================
// SLIDE 6 — Root cause: low-quality acquisition surge
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "The root cause", { color: WARN });
  title(s, "The cause: an acquisition surge, months back");

  // left: MobileZone share of new adds over time
  s.addChart(pres.ChartType.line,
    [{ name: "MobileZone share of new adds %", labels: mzShare.labels.slice(18), values: mzShare.mobilezone_share.slice(18) }],
    {
      x: 0.6, y: 1.95, w: 5.9, h: 3.6,
      chartColors: [WARN], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 4,
      showTitle: true, title: "MobileZone's share of company-wide new adds (last 18 months)",
      titleFontSize: 11.5, titleColor: INK, titleFontFace: FONT,
      showLegend: false, showValue: false,
      catAxisLabelColor: MUTE, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 7.5, valAxisLabelFontSize: 9, catAxisLabelRotate: 45,
      valGridLine: { color: "E3E7EF", size: 1 }, catGridLine: { style: "none" },
      valAxisTitle: "%", showValAxisTitle: true, valAxisTitleFontSize: 9,
    }
  );

  // right: 180-day cohort churn by dealer
  const cohortColors = cohortChurn.dealers.map(d => d === "MobileZone" ? WARN : "C9CEDC");
  s.addChart(pres.ChartType.bar,
    [{ name: "% churned within 180 days", labels: cohortChurn.dealers, values: cohortChurn.pct }],
    {
      x: 7.0, y: 1.95, w: 5.7, h: 3.6,
      barDir: "bar",
      chartColorsOpacity: 100,
      chartColors: cohortColors,
      showTitle: true, title: "% of H1-2025 join cohort already churned within 180 days",
      titleFontSize: 11.5, titleColor: INK, titleFontFace: FONT,
      showLegend: false, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9,
      catAxisLabelColor: INK, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 9,
      valGridLine: { color: "E3E7EF", size: 1 }, catGridLine: { style: "none" },
      valAxisTitle: "%", showValAxisTitle: true, valAxisTitleFontSize: 9,
    }
  );

  s.addText([
    { text: "In H1 2025, MobileZone captured ", options: {} },
    { text: "~40% of all new subscribers", options: { bold: true, color: WARN } },
    { text: " company-wide — more than double its normal 15–19% share. ", options: {} },
    { text: "43% of that cohort", options: { bold: true, color: WARN } },
    { text: " had already churned by year-end (median tenure ~6 months) — a churn speed far outside normal cohort behavior.", options: {} },
  ], {
    x: 0.6, y: 5.75, w: 12.1, h: 1.0, fontFace: FONT, fontSize: 13.5, color: INK,
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
  });
  pageNum(s, 6);
}

// =====================================================================
// SLIDE 7 — Financial impact: budget beat turns to miss
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "Why it matters", { color: WARN });
  title(s, "The 2025 budget flips from beat to miss in Q4");

  s.addChart(pres.ChartType.bar,
    [
      { name: "Actual revenue (₪k)", labels: revVsBudget.labels, values: revVsBudget.actual },
      { name: "Budget (₪k)", labels: revVsBudget.labels, values: revVsBudget.budget },
    ],
    {
      x: 0.6, y: 1.9, w: 5.9, h: 4.3,
      barDir: "col", barGapWidthPct: 30,
      chartColors: [NAVY, "B9C2D6"],
      showTitle: true, title: "Actual vs. budget revenue, 2025 (₪k/month)",
      titleFontSize: 12, titleColor: INK, titleFontFace: FONT,
      showLegend: true, legendPos: "b", legendFontSize: 9,
      showValue: false,
      catAxisLabelColor: MUTE, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 8,
      valGridLine: { color: "E3E7EF", size: 1 }, catGridLine: { style: "none" },
    }
  );

  s.addChart(pres.ChartType.bar,
    [{ name: "Cumulative YTD variance (₪k)", labels: cumVariance.labels, values: cumVariance.cum_variance_k }],
    {
      x: 7.0, y: 1.9, w: 5.7, h: 4.3,
      barDir: "col",
      chartColors: [WARN],
      showTitle: true, title: "Cumulative YTD budget variance, 2025 (₪k)",
      titleFontSize: 12, titleColor: INK, titleFontFace: FONT,
      showLegend: false, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 8,
      catAxisLabelColor: MUTE, valAxisLabelColor: MUTE,
      catAxisLabelFontSize: 9, valAxisLabelFontSize: 8,
      valGridLine: { color: "E3E7EF", size: 1 }, catGridLine: { style: "none" },
    }
  );

  s.addText("Beating budget by +₪24.4k through September → missing by –₪80.5k cumulative by December — the same months churn accelerated.", {
    x: 0.6, y: 6.45, w: 12, h: 0.6, fontFace: FONT, fontSize: 13.5, bold: true, color: WARN,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 7);
}

// =====================================================================
// SLIDE 8 — Recommendations
// =====================================================================
{
  const s = darkSlide();
  kicker(s, "What we recommend", { color: ICE });
  title(s, "Four moves, in order", { color: WHITE });

  const recs = [
    { n: "1", h: "Investigate", b: "Pull MobileZone's H1-2025 sales/incentive practices — promo, subsidy, or quota push behind the surge." },
    { n: "2", h: "Contain", b: "Cap or closely monitor new activations through MobileZone until the cause is confirmed and fixed." },
    { n: "3", h: "Make it structural", b: "Track dealer performance on 90/180-day retention, not gross adds alone — this is exactly what let it run two quarters unnoticed." },
    { n: "4", h: "Re-forecast", b: "Flag 2025 year-end and 2026 budget assumptions for revision if the book doesn't stabilize." },
  ];
  let ry = 2.0;
  recs.forEach((r) => {
    s.addShape(pres.ShapeType.ellipse, {
      x: 0.7, y: ry, w: 0.55, h: 0.55, fill: { color: WARN }, line: { type: "none" },
    });
    s.addText(r.n, {
      x: 0.7, y: ry, w: 0.55, h: 0.55, fontFace: HEAD_FONT, fontSize: 20, bold: true,
      color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0,
    });
    s.addText(r.h, {
      x: 1.55, y: ry - 0.05, w: 3.0, h: 0.6, fontFace: HEAD_FONT, fontSize: 19, bold: true,
      color: WHITE, isTextBox: true, margin: 0, valign: "middle",
    });
    s.addText(r.b, {
      x: 4.7, y: ry - 0.05, w: 8.0, h: 0.7, fontFace: FONT, fontSize: 13.5, color: ICE,
      isTextBox: true, margin: 0, valign: "middle",
    });
    ry += 1.15;
  });
  pageNum(s, 8);
}

// =====================================================================
// SLIDE 9 — Methodology & assumptions
// =====================================================================
{
  const s = lightSlide();
  kicker(s, "How we got here");
  title(s, "Methodology & Assumptions");
  s.addText("Every number here is defensible — full detail lives in the data-quality memo.", {
    x: 0.6, y: 1.55, w: 12, h: 0.4, fontFace: FONT, fontSize: 14, italic: true, color: MUTE,
    isTextBox: true, margin: 0,
  });

  const cols = [
    {
      h: "Data quality first",
      items: [
        "Profiled all 6 source files before analysis: nulls, duplicate keys, referential integrity",
        "Standardized dealer_code (39 raw spellings → 10 dealers)",
        "Deduped a legacy-named plan_code row",
      ],
    },
    {
      h: "Documented assumptions",
      items: [
        "Budget's “Jerusalem & South” reconciled against 5-way district split via a bridge mapping",
        "Churn month counts as active (final partial-month bill)",
        "billed_amount used as-is as net revenue (no overage breakout in source data)",
      ],
    },
    {
      h: "Model & scope",
      items: [
        "Star schema: subscriber-month billing fact + district-month budget fact",
        "3,678 subscribers (7.2%) churned before the billing window (2023-07) starts — excluded from revenue/churn measures, kept in dimension",
        "Full detail in the data-quality memo (Phase 1 deliverable)",
      ],
    },
  ];
  let cx = 0.6;
  cols.forEach((c) => {
    s.addText(c.h, {
      x: cx, y: 2.15, w: 3.9, h: 0.5, fontFace: HEAD_FONT, fontSize: 16, bold: true, color: NAVY,
      isTextBox: true, margin: 0,
    });
    const para = c.items.map((it, i) => ({
      text: it,
      options: { bullet: { code: "2022" }, breakLine: i < c.items.length - 1, paraSpaceAfter: 10 },
    }));
    s.addText(para, {
      x: cx, y: 2.7, w: 3.9, h: 3.8, fontFace: FONT, fontSize: 12.5, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
    cx += 4.15;
  });
  s.addText("Full data-quality memo, star schema, and DAX measure library available on request / in the supporting workbook.", {
    x: 0.6, y: 6.7, w: 12, h: 0.4, fontFace: FONT, fontSize: 11, italic: true, color: MUTE,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 9);
}

// =====================================================================
// SLIDE 10 — Close / dashboard + next steps
// =====================================================================
{
  const s = darkSlide();
  kicker(s, "Next steps", { color: ICE });
  title(s, "A standing dashboard, not a one-time report", { color: WHITE, size: 28 });

  const items = [
    { h: "Executive Overview", b: "Weekly-monitoring page: revenue, churn, ARPU, subscriber trend" },
    { h: "Budget Performance", b: "Actual vs. budget by district/month, YTD variance" },
    { h: "Dealer & Churn Driver", b: "The finding, live: retention-by-dealer, cohort quality, always on" },
  ];
  let cx = 0.7;
  items.forEach((it) => {
    s.addShape(pres.ShapeType.roundRect, {
      x: cx, y: 2.3, w: 3.85, h: 2.6, rectRadius: 0.08,
      fill: { color: "252E63" }, line: { color: "3A4590", width: 1 },
    });
    s.addText(it.h, {
      x: cx + 0.3, y: 2.6, w: 3.25, h: 0.7, fontFace: HEAD_FONT, fontSize: 17, bold: true,
      color: ICE, isTextBox: true, margin: 0,
    });
    s.addText(it.b, {
      x: cx + 0.3, y: 3.35, w: 3.25, h: 1.4, fontFace: FONT, fontSize: 12.5, color: WHITE,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.2,
    });
    cx += 4.1;
  });

  s.addText("Recommendation: revisit acquisition-quality KPIs monthly — this is the metric that would have caught it in July, not January.", {
    x: 0.7, y: 5.4, w: 11.9, h: 0.6, fontFace: FONT, fontSize: 14, italic: true, color: ICE,
    isTextBox: true, margin: 0,
  });
  s.addText("Thank you", {
    x: 0.7, y: 6.3, w: 6, h: 0.7, fontFace: HEAD_FONT, fontSize: 24, bold: true, color: WHITE,
    isTextBox: true, margin: 0,
  });
  pageNum(s, 10);
}

pres.writeFile({ fileName: "/home/user/home-assignment-/deck/NexWave_Mobile_Business_Review.pptx" }).then(() => {
  console.log("Deck written.");
});
