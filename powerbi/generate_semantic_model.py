"""
Generates a Power BI Project (.pbip) with a fully-built TMDL semantic model
for the NexWave Mobile star schema, from a single source of truth so table/
column/relationship/measure definitions can be statically cross-checked
before anyone opens this in Power BI Desktop (which isn't available here).

Run: python3 generate_semantic_model.py
Output: ./NexWave Mobile.pbip, ./NexWave Mobile.Report/, ./NexWave Mobile.SemanticModel/
"""
import json
import os
import shutil
import uuid

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_NAME = "NexWave Mobile"
SEMANTIC_DIR = os.path.join(BASE, f"{PROJECT_NAME}.SemanticModel")
REPORT_DIR = os.path.join(BASE, f"{PROJECT_NAME}.Report")
PBIP_PATH = os.path.join(BASE, f"{PROJECT_NAME}.pbip")

TAB = "\t"

def guid():
    return str(uuid.uuid4())

# =============================================================================
# SCHEMA DEFINITION (single source of truth) -- mirrors data/clean/*.csv exactly
# =============================================================================

# column: (name, m_type_literal, dax_data_type)
# m_type_literal is what goes inside Table.TransformColumnTypes' {{"col", <this>}}
# dax_data_type is the TMDL `dataType:` value

TABLES = {
    "dim_district": {
        "csv_columns": 1,
        "columns": [
            ("district", "type text", "string"),
        ],
        "bool_columns": [],
        "date_columns": [],
    },
    "dim_customer": {
        "csv_columns": 5,
        "columns": [
            ("customer_id", "type text", "string"),
            ("segment", "type text", "string"),
            ("city", "type text", "string"),
            ("district_detail", "type text", "string"),
            ("district", "type text", "string"),
        ],
        "bool_columns": [],
        "date_columns": [],
    },
    "dim_dealer": {
        "csv_columns": 6,
        "columns": [
            ("dealer_code", "type text", "string"),
            ("dealer_name", "type text", "string"),
            ("dealer_type", "type text", "string"),
            ("city", "type text", "string"),
            ("district_detail", "type text", "string"),
            ("district", "type text", "string"),
        ],
        "bool_columns": [],
        "date_columns": [],
    },
    "dim_plan": {
        "csv_columns": 5,
        "columns": [
            ("plan_code", "type text", "string"),
            ("plan_name", "type text", "string"),
            ("plan_family", "type text", "string"),
            ("monthly_list_price", "Int64.Type", "int64"),
        ],
        "bool_columns": ["is_legacy_plan"],
        "date_columns": [],
    },
    "dim_subscriber": {
        "csv_columns": 9,
        "columns": [
            ("subscriber_id", "type text", "string"),
            ("customer_id", "type text", "string"),
            ("dealer_code", "type text", "string"),
            ("plan_code", "type text", "string"),
            ("status", "type text", "string"),
            ("tenure_days", "Int64.Type", "int64"),
        ],
        "bool_columns": ["in_billing_window"],
        "date_columns": ["join_date", "churn_date"],
    },
    "dim_date": {
        "csv_columns": 14,
        "columns": [
            ("year", "Int64.Type", "int64"),
            ("quarter", "type text", "string"),
            ("year_quarter", "type text", "string"),
            ("month_num", "Int64.Type", "int64"),
            ("month_name", "type text", "string"),
            ("month_short", "type text", "string"),
            ("year_month", "type text", "string"),
            ("year_month_label", "type text", "string"),
            ("day_of_month", "Int64.Type", "int64"),
            ("fiscal_year", "Int64.Type", "int64"),
            ("fiscal_quarter", "type text", "string"),
        ],
        "bool_columns": ["is_month_start", "is_month_end"],
        "date_columns": ["date"],
    },
    "fact_billing": {
        "csv_columns": 3,
        "columns": [
            ("subscriber_id", "type text", "string"),
            ("billed_amount", "type number", "double"),
        ],
        "bool_columns": [],
        "date_columns": ["date"],
    },
    "fact_budget": {
        "csv_columns": 4,
        "columns": [
            ("district", "type text", "string"),
            ("line_item", "type text", "string"),
            ("budget_amount", "type number", "double"),
        ],
        "bool_columns": [],
        "date_columns": ["date"],
    },
}

# CSV header order per table (must match data/clean/*.csv exactly, drives the
# Csv.Document -> Table.TransformColumnTypes M step)
CSV_HEADERS = {
    "dim_district": ["district"],
    "dim_customer": ["customer_id", "segment", "city", "district_detail", "district"],
    "dim_dealer": ["dealer_code", "dealer_name", "dealer_type", "city", "district_detail", "district"],
    "dim_plan": ["plan_code", "plan_name", "plan_family", "monthly_list_price", "is_legacy_plan"],
    "dim_subscriber": ["subscriber_id", "customer_id", "dealer_code", "plan_code", "join_date",
                       "churn_date", "status", "in_billing_window", "tenure_days"],
    "dim_date": ["date", "year", "quarter", "year_quarter", "month_num", "month_name", "month_short",
                 "year_month", "year_month_label", "day_of_month", "is_month_start", "is_month_end",
                 "fiscal_year", "fiscal_quarter"],
    "fact_billing": ["subscriber_id", "date", "billed_amount"],
    "fact_budget": ["district", "date", "line_item", "budget_amount"],
}

# relationships: (from_table.column [many side], to_table.column [one side])
RELATIONSHIPS = [
    ("dim_customer.district", "dim_district.district"),
    ("dim_dealer.district", "dim_district.district"),
    ("fact_budget.district", "dim_district.district"),
    ("dim_subscriber.customer_id", "dim_customer.customer_id"),
    ("dim_subscriber.dealer_code", "dim_dealer.dealer_code"),
    ("dim_subscriber.plan_code", "dim_plan.plan_code"),
    ("fact_billing.subscriber_id", "dim_subscriber.subscriber_id"),
    ("fact_billing.date", "dim_date.date"),
    ("fact_budget.date", "dim_date.date"),
]

# measures: (name, dax_body_lines, format_string, description)
MEASURES = [
    ("Total Revenue", [
        "SUM(fact_billing[billed_amount])",
    ], '"#,##0"', "Net billed revenue for whatever filter context is active."),

    ("Revenue MoM %", [
        "VAR CurrentRevenue = [Total Revenue]",
        "VAR PriorMonthRevenue =",
        "    CALCULATE([Total Revenue], DATEADD(dim_date[date], -1, MONTH))",
        "RETURN",
        "    DIVIDE(CurrentRevenue - PriorMonthRevenue, PriorMonthRevenue)",
    ], '"0.0%;-0.0%;0.0%"', "Month-over-month revenue growth."),

    ("Revenue YoY %", [
        "VAR CurrentRevenue = [Total Revenue]",
        "VAR PriorYearRevenue =",
        "    CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[date]))",
        "RETURN",
        "    DIVIDE(CurrentRevenue - PriorYearRevenue, PriorYearRevenue)",
    ], '"0.0%;-0.0%;0.0%"', "Year-over-year revenue growth. Blank before 2024-07 (no prior year in fact_billing)."),

    ("Revenue Trailing 3M", [
        "CALCULATE(",
        "    [Total Revenue],",
        "    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -3, MONTH)",
        ")",
    ], '"#,##0"', "Trailing 3-month revenue, smooths single-month noise."),

    ("Revenue Trailing 12M", [
        "CALCULATE(",
        "    [Total Revenue],",
        "    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -12, MONTH)",
        ")",
    ], '"#,##0"', "Trailing 12-month revenue."),

    ("Active Subscribers (EOP)", [
        "VAR LastDateInContext = MAX(dim_date[date])",
        "VAR TargetMonthStart = DATE(YEAR(LastDateInContext), MONTH(LastDateInContext), 1)",
        "RETURN",
        "CALCULATE(",
        "    DISTINCTCOUNT(fact_billing[subscriber_id]),",
        "    fact_billing[date] = TargetMonthStart",
        ")",
    ], '"#,##0"', "End-of-period active subscriber snapshot (last month in the filter context, not summed across it)."),

    ("Active Subscribers (BOP)", [
        "VAR LastDateInContext = MAX(dim_date[date])",
        "VAR TargetMonthStart = DATE(YEAR(LastDateInContext), MONTH(LastDateInContext), 1)",
        "VAR PriorMonthStart = EDATE(TargetMonthStart, -1)",
        "RETURN",
        "CALCULATE(",
        "    DISTINCTCOUNT(fact_billing[subscriber_id]),",
        "    fact_billing[date] = PriorMonthStart",
        ")",
    ], '"#,##0"', "Beginning-of-period active subscribers -- the churn-rate denominator."),

    ("New Subscribers (Gross Adds)", [
        "VAR PeriodStart = MIN(dim_date[date])",
        "VAR PeriodEnd = MAX(dim_date[date])",
        "RETURN",
        "CALCULATE(",
        "    COUNTROWS(dim_subscriber),",
        "    dim_subscriber[join_date] >= PeriodStart,",
        "    dim_subscriber[join_date] <= PeriodEnd",
        ")",
    ], '"#,##0"', "Subscribers who joined within the selected period."),

    ("Churned Subscribers", [
        "VAR PeriodStart = MIN(dim_date[date])",
        "VAR PeriodEnd = MAX(dim_date[date])",
        "RETURN",
        "CALCULATE(",
        "    COUNTROWS(dim_subscriber),",
        "    dim_subscriber[churn_date] >= PeriodStart,",
        "    dim_subscriber[churn_date] <= PeriodEnd",
        ")",
    ], '"#,##0"', "Subscribers who churned within the selected period."),

    ("Net Subscriber Adds", [
        "[New Subscribers (Gross Adds)] - [Churned Subscribers]",
    ], '"#,##0"', "Gross adds minus churn."),

    ("Churn Rate (Monthly %)", [
        "DIVIDE([Churned Subscribers], [Active Subscribers (BOP)])",
    ], '"0.00%;-0.00%;0.00%"', "Monthly churn rate -- the primary health metric."),

    ("Churn Rate Trailing 3M (Avg)", [
        "AVERAGEX(",
        "    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -3, MONTH),",
        "    [Churn Rate (Monthly %)]",
        ")",
    ], '"0.00%;-0.00%;0.00%"', "Trailing 3-month average churn rate, smooths noise."),

    ("ARPU", [
        "DIVIDE([Total Revenue], [Active Subscribers (EOP)])",
    ], '"#,##0.00"', "Average revenue per subscriber for the period in context."),

    ("ARPU MoM %", [
        "VAR CurrentARPU = [ARPU]",
        "VAR PriorMonthARPU = CALCULATE([ARPU], DATEADD(dim_date[date], -1, MONTH))",
        "RETURN",
        "    DIVIDE(CurrentARPU - PriorMonthARPU, PriorMonthARPU)",
    ], '"0.0%;-0.0%;0.0%"', "Month-over-month ARPU change."),

    ("Budget Revenue", [
        "SUM(fact_budget[budget_amount])",
    ], '"#,##0"', "2025 budgeted service revenue (district/month grain only)."),

    ("Budget Variance", [
        "[Total Revenue] - [Budget Revenue]",
    ], '"#,##0;-#,##0"', "Actual minus budget, in currency."),

    ("Budget Variance %", [
        "DIVIDE([Budget Variance], [Budget Revenue])",
    ], '"0.0%;-0.0%;0.0%"', "Budget variance as a percentage of budget."),

    ("Budget Variance YTD", [
        "VAR ActualYTD = CALCULATE([Total Revenue], DATESYTD(dim_date[date]))",
        "VAR BudgetYTD = CALCULATE([Budget Revenue], DATESYTD(dim_date[date]))",
        "RETURN",
        "    ActualYTD - BudgetYTD",
    ], '"#,##0;-#,##0"', "Cumulative year-to-date budget variance."),

    ("% Subscribers on Legacy Plans", [
        "VAR LegacyActive =",
        "    CALCULATE(",
        "        COUNTROWS(dim_subscriber),",
        "        dim_plan[is_legacy_plan] = TRUE,",
        '        dim_subscriber[status] = "Active"',
        "    )",
        "VAR TotalActive =",
        "    CALCULATE(",
        "        COUNTROWS(dim_subscriber),",
        '        dim_subscriber[status] = "Active"',
        "    )",
        "RETURN",
        "    DIVIDE(LegacyActive, TotalActive)",
    ], '"0.0%;-0.0%;0.0%"', "Share of the active base still on a legacy/plus plan code."),

    ("New Subscriber Share %", [
        "VAR PeriodStart = MIN(dim_date[date])",
        "VAR PeriodEnd = MAX(dim_date[date])",
        "VAR DealerAdds = [New Subscribers (Gross Adds)]",
        "VAR CompanyAdds =",
        "    CALCULATE(",
        "        COUNTROWS(dim_subscriber),",
        "        REMOVEFILTERS(dim_dealer),",
        "        dim_subscriber[join_date] >= PeriodStart,",
        "        dim_subscriber[join_date] <= PeriodEnd",
        "    )",
        "RETURN",
        "    DIVIDE(DealerAdds, CompanyAdds)",
    ], '"0.0%;-0.0%;0.0%"', "A dealer's share of that period's total new-subscriber adds."),

    ("180-Day Cohort Churn Rate", [
        "VAR CohortSize = COUNTROWS(dim_subscriber)",
        "VAR CohortChurned180 =",
        "    CALCULATE(",
        "        COUNTROWS(dim_subscriber),",
        "        dim_subscriber[Churned Within 180 Days] = TRUE",
        "    )",
        "RETURN",
        "    DIVIDE(CohortChurned180, CohortSize)",
    ], '"0.0%;-0.0%;0.0%"',
     "Of subscribers who joined in the selected period, % already churned within 180 days. "
     "Use with a slicer on dim_subscriber[join_date], not dim_date."),
]

CALCULATED_COLUMNS = {
    "dim_subscriber": [
        ("Churned Within 180 Days",
         'NOT ISBLANK(dim_subscriber[churn_date]) && '
         'DATEDIFF(dim_subscriber[join_date], dim_subscriber[churn_date], DAY) <= 180',
         "boolean"),
    ],
}

# =============================================================================
# STATIC VALIDATION -- catch typos before anyone opens this in Power BI Desktop
# =============================================================================

def validate_schema():
    errors = []
    all_known_tables = set(TABLES) | {"_Measures"}

    for tname, spec in TABLES.items():
        expected_cols = set(CSV_HEADERS[tname])
        declared_cols = {c[0] for c in spec["columns"]} | set(spec["bool_columns"]) | set(spec["date_columns"])
        if declared_cols != expected_cols:
            errors.append(f"{tname}: declared columns {declared_cols} != csv headers {expected_cols}")
        if len(CSV_HEADERS[tname]) != spec["csv_columns"]:
            errors.append(f"{tname}: csv_columns count mismatch")

    for frm, to in RELATIONSHIPS:
        ftab, fcol = frm.split(".")
        ttab, tcol = to.split(".")
        for tab, col in [(ftab, fcol), (ttab, tcol)]:
            if tab not in all_known_tables:
                errors.append(f"relationship references unknown table: {tab}")
                continue
            spec = TABLES[tab]
            known = {c[0] for c in spec["columns"]} | set(spec["bool_columns"]) | set(spec["date_columns"])
            if col not in known:
                errors.append(f"relationship references unknown column: {tab}.{col}")

    measure_names = {m[0] for m in MEASURES}
    import re
    col_ref_re = re.compile(r"(\w+)\[([^\]]+)\]")
    measure_ref_re = re.compile(r"(?<!\w)\[([^\]]+)\]")
    for name, lines, fmt, desc in MEASURES:
        text = "\n".join(lines)
        for tab, col in col_ref_re.findall(text):
            if tab in ("dim_subscriber",) and col == "Churned Within 180 Days":
                continue  # calculated column, checked separately
            if tab in TABLES:
                known = {c[0] for c in TABLES[tab]["columns"]} | set(TABLES[tab]["bool_columns"]) | set(TABLES[tab]["date_columns"])
                if col not in known:
                    errors.append(f"measure '{name}' references unknown column {tab}[{col}]")
        for ref in measure_ref_re.findall(text):
            if ref in measure_names:
                continue
            # bracket refs to the same measure's own name (recursive, shouldn't happen) or typo
            errors.append(f"measure '{name}' references unknown measure or column [{ref}]")

    for tab, cols in CALCULATED_COLUMNS.items():
        if tab not in TABLES:
            errors.append(f"calculated column table unknown: {tab}")

    if errors:
        raise SystemExit("SCHEMA VALIDATION FAILED:\n" + "\n".join(f"  - {e}" for e in errors))
    print(f"Schema validation passed: {len(TABLES)} tables, {len(RELATIONSHIPS)} relationships, {len(MEASURES)} measures.")

validate_schema()

# =============================================================================
# M CODE GENERATION
# =============================================================================

def m_type_pairs(table_name):
    spec = TABLES[table_name]
    return [(c[0], c[1]) for c in spec["columns"]]

def build_m_steps(table_name):
    spec = TABLES[table_name]
    n = spec["csv_columns"]
    steps = []  # list of (step_name_expr, m_expression) in order; step_name_expr already quoted as needed

    steps.append(('Source',
        'Csv.Document(File.Contents(DataFolderPath & "%s.csv"), [Delimiter=",", Columns=%d, Encoding=65001, QuoteStyle=QuoteStyle.None])'
        % (table_name, n)))
    steps.append(('#"Promoted Headers"', 'Table.PromoteHeaders(Source, [PromoteAllScalars=true])'))
    prev = '#"Promoted Headers"'

    pairs = m_type_pairs(table_name)
    if pairs:
        pair_str = ", ".join('{"%s", %s}' % (c, t) for c, t in pairs)
        steps.append(('#"Changed Type"', 'Table.TransformColumnTypes(%s, {%s})' % (prev, pair_str)))
        prev = '#"Changed Type"'

    for bc in spec["bool_columns"]:
        step = '#"Fixed %s"' % bc
        expr = ('Table.TransformColumns(%s, {{"%s", each Text.Upper(Text.Trim(Text.From(_))) = "TRUE", type logical}})'
                % (prev, bc))
        steps.append((step, expr))
        prev = step

    for dc in spec["date_columns"]:
        step = '#"Fixed %s"' % dc
        expr = ('Table.TransformColumns(%s, {{"%s", each if _ = null or _ = "" then null else Date.FromText(_), type date}})'
                % (prev, dc))
        steps.append((step, expr))
        prev = step

    return steps, prev

def render_m_source(table_name):
    steps, last = build_m_steps(table_name)
    lines = ["let"]
    for name, expr in steps:
        lines.append("    %s = %s," % (name, expr))
    # strip trailing comma on the final let-step
    lines[-1] = lines[-1].rstrip(",")
    lines.append("in")
    lines.append("    " + last)
    return "\n".join(lines)

# =============================================================================
# TMDL RENDERING
# =============================================================================

def indent_block(text, levels):
    prefix = TAB * levels
    return "\n".join(prefix + line if line.strip() else line for line in text.split("\n"))

def render_table_tmdl(table_name):
    spec = TABLES[table_name]
    out = []
    out.append('table %s' % table_name)
    out.append('%slineageTag: %s' % (TAB, guid()))
    out.append('')

    def col_block(col, dtype, format_string=None):
        b = []
        b.append('%scolumn %s' % (TAB, col if " " not in col else "'%s'" % col))
        b.append('%s%sdataType: %s' % (TAB, TAB, dtype))
        if format_string:
            b.append('%s%sformatString: %s' % (TAB, TAB, format_string))
        b.append('%s%slineageTag: %s' % (TAB, TAB, guid()))
        b.append('%s%ssummarizeBy: none' % (TAB, TAB))
        b.append('%s%ssourceColumn: %s' % (TAB, TAB, col))
        b.append('')
        b.append('%s%sannotation SummarizationSetBy = Automatic' % (TAB, TAB))
        b.append('')
        return "\n".join(b)

    for col, _, dtype in spec["columns"]:
        out.append(col_block(col, dtype))
    for col in spec["bool_columns"]:
        out.append(col_block(col, "boolean"))
    for col in spec["date_columns"]:
        out.append(col_block(col, "dateTime", format_string="Short Date"))

    for col, expr, dtype in CALCULATED_COLUMNS.get(table_name, []):
        out.append('%scolumn %s = %s' % (TAB, "'%s'" % col if " " in col else col, expr))
        out.append('%s%sdataType: %s' % (TAB, TAB, dtype))
        out.append('%s%slineageTag: %s' % (TAB, TAB, guid()))
        out.append('%s%ssummarizeBy: none' % (TAB, TAB))
        out.append('')
        out.append('%s%sannotation SummarizationSetBy = Automatic' % (TAB, TAB))
        out.append('')

    m_source = render_m_source(table_name)
    out.append('%spartition %s = m' % (TAB, table_name))
    out.append('%s%smode: import' % (TAB, TAB))
    out.append('%s%ssource =' % (TAB, TAB))
    out.append(indent_block(m_source, 4))
    out.append('')
    out.append('%sannotation PBI_ResultType = Table' % TAB)
    out.append('')
    return "\n".join(out)

def render_measures_table_tmdl():
    out = []
    out.append('table _Measures')
    out.append('%slineageTag: %s' % (TAB, guid()))
    out.append('%sisHidden' % TAB)
    out.append('')
    out.append('%scolumn _' % TAB)
    out.append('%s%sdataType: int64' % (TAB, TAB))
    out.append('%s%slineageTag: %s' % (TAB, TAB, guid()))
    out.append('%s%sisHidden' % (TAB, TAB))
    out.append('%s%ssummarizeBy: none' % (TAB, TAB))
    out.append('%s%ssourceColumn: _' % (TAB, TAB))
    out.append('')
    out.append('%s%sannotation SummarizationSetBy = Automatic' % (TAB, TAB))
    out.append('')
    for name, body_lines, fmt, desc in MEASURES:
        measure_name = "'%s'" % name if (" " in name or "%" in name or "(" in name) else name
        dax = "\n".join(body_lines)
        out.append('%smeasure %s =' % (TAB, measure_name))
        out.append('%s%s```' % (TAB, TAB))
        for l in body_lines:
            out.append('%s%s%s' % (TAB, TAB, l))
        out.append('%s%s```' % (TAB, TAB))
        out.append('%s%sformatString: %s' % (TAB, TAB, fmt))
        out.append('%s%slineageTag: %s' % (TAB, TAB, guid()))
        out.append('')
        out.append('%s%sannotation PBI_FormatHint = {"isGeneralNumber":true}' % (TAB, TAB))
        out.append('')
    out.append('%spartition _Measures = m' % TAB)
    out.append('%s%smode: import' % (TAB, TAB))
    out.append('%s%ssource =' % (TAB, TAB))
    out.append('%s%s%s#table(type table [_ = Int64.Type], {})' % (TAB, TAB, TAB))
    out.append('')
    out.append('%sannotation PBI_ResultType = Table' % TAB)
    out.append('')
    return "\n".join(out)

def render_relationships_tmdl():
    out = []
    for frm, to in RELATIONSHIPS:
        out.append('relationship %s' % guid())
        out.append('%sfromColumn: %s' % (TAB, frm))
        out.append('%stoColumn: %s' % (TAB, to))
        out.append('')
    return "\n".join(out)

def render_expressions_tmdl():
    out = []
    out.append(r'expression DataFolderPath = "C:\CHANGE_ME\data\clean\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]')
    out.append('%slineageTag: %s' % (TAB, guid()))
    out.append('')
    out.append('%sannotation PBI_ResultType = Text' % TAB)
    out.append('')
    return "\n".join(out)

def render_model_tmdl():
    table_order = list(TABLES.keys()) + ["_Measures"]
    out = []
    out.append('model Model')
    out.append('%sculture: en-US' % TAB)
    out.append('%sdefaultPowerBIDataSourceVersion: powerBI_V3' % TAB)
    out.append('%ssourceQueryCulture: en-US' % TAB)
    out.append('%sdataAccessOptions' % TAB)
    out.append('%s%slegacyRedirects' % (TAB, TAB))
    out.append('%s%sreturnErrorValuesAsNull' % (TAB, TAB))
    out.append('')
    out.append('annotation PBI_QueryOrder = ["%s"]' % '","'.join(table_order))
    out.append('')
    out.append('annotation __PBI_TimeIntelligenceEnabled = 1')
    out.append('')
    out.append('ref expression DataFolderPath')
    for t in table_order:
        out.append('ref table %s' % t)
    out.append('')
    return "\n".join(out)

def render_database_tmdl():
    return "database\n%scompatibilityLevel: 1567\n" % TAB

# =============================================================================
# FILE WRITING
# =============================================================================

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(content)
        if not content.endswith("\n"):
            f.write("\n")

def main():
    if os.path.isdir(SEMANTIC_DIR):
        shutil.rmtree(SEMANTIC_DIR)
    if os.path.isdir(REPORT_DIR):
        shutil.rmtree(REPORT_DIR)

    # ---- SemanticModel ----
    def_dir = os.path.join(SEMANTIC_DIR, "definition")
    write(os.path.join(def_dir, "database.tmdl"), render_database_tmdl())
    write(os.path.join(def_dir, "model.tmdl"), render_model_tmdl())
    write(os.path.join(def_dir, "relationships.tmdl"), render_relationships_tmdl())
    write(os.path.join(def_dir, "expressions.tmdl"), render_expressions_tmdl())

    for t in TABLES:
        write(os.path.join(def_dir, "tables", "%s.tmdl" % t), render_table_tmdl(t))
    write(os.path.join(def_dir, "tables", "_Measures.tmdl"), render_measures_table_tmdl())

    write(os.path.join(SEMANTIC_DIR, "definition.pbism"),
          json.dumps({"version": "4.2", "settings": {}}, indent=2))

    write(os.path.join(SEMANTIC_DIR, ".platform"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": PROJECT_NAME},
        "config": {"version": "2.0", "logicalId": guid()}
    }, indent=2))

    # ---- Report (minimal single blank page shell) ----
    write(os.path.join(REPORT_DIR, "definition.pbir"), json.dumps({
        "version": "1.0",
        "datasetReference": {"byPath": {"path": "../%s.SemanticModel" % PROJECT_NAME}}
    }, indent=2))

    write(os.path.join(REPORT_DIR, ".platform"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": PROJECT_NAME},
        "config": {"version": "2.0", "logicalId": guid()}
    }, indent=2))

    report_json = {
        "config": json.dumps({
            "version": "5.45",
            "themeCollection": {"baseTheme": {"name": "CY23SU08"}},
            "activeSectionIndex": 0,
        }),
        "layoutOptimization": 0,
        "sections": [
            {
                "name": "ReportSection1",
                "displayName": "Start here — build per docs/05_dashboard_spec.md",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": [],
                "config": "{}",
                "width": 1280,
                "height": 720,
            }
        ],
        "resourcePackages": [],
    }
    write(os.path.join(REPORT_DIR, "report.json"), json.dumps(report_json, indent=2))

    # ---- top-level .pbip pointer ----
    write(PBIP_PATH, json.dumps({
        "version": "1.0",
        "artifacts": [{"report": {"path": "%s.Report" % PROJECT_NAME}}],
        "settings": {"enableAutoRecovery": True}
    }, indent=2))

    print("Wrote:")
    print(" ", PBIP_PATH)
    print(" ", REPORT_DIR)
    print(" ", SEMANTIC_DIR)

if __name__ == "__main__":
    main()
