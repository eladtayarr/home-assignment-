# NexWave Mobile — Power BI Project (.pbip)

## What's in here

- **`NexWave Mobile.SemanticModel/`** — the full data model, hand-authored as
  TMDL (Tabular Model Definition Language): all 8 tables, all 9 relationships,
  and all 21 DAX measures from `docs/03_dax_measures.md`, wired up exactly per
  `docs/02_data_model.md`. This is the part that would otherwise take the most
  manual clicking/typing to recreate in Power BI Desktop — it's done.
- **`NexWave Mobile.Report/`** — a minimal, essentially blank report shell (one
  page, no visuals). Build the 3 real pages here yourself following
  `docs/05_dashboard_spec.md` — that part is inherently a "look at it and
  arrange visuals" task better done by a human in the actual tool.
- **`NexWave Mobile.pbip`** — the project pointer file. Double-click this (or
  open it from Power BI Desktop) to load everything above.

## Why it's built this way

A `.pbix` file is a proprietary binary Power BI Desktop compiles — it can't be
generated from outside Desktop. The `.pbip` project format (Nov 2023+) is
different: it's plain text (TMDL + JSON), designed to be hand-edited and
opened directly in Desktop. That's what this is. **I have no Power BI Desktop
in this environment to open or test this file myself** — everything below is
validated as far as it can be without that (see "How this was checked"), but
you are the first to actually open it.

## Before you open it: one required edit

The model reads its data from CSV files via a text parameter,
**`DataFolderPath`**, currently set to a placeholder:
`C:\CHANGE_ME\data\clean\`. Before (or right after) opening the file:

1. Copy this repo's `data/clean/` folder somewhere on your machine (or note
   its path if you clone the whole repo).
2. Open `NexWave Mobile.SemanticModel/definition/expressions.tmdl` in a text
   editor and change the path to your actual folder — e.g.
   `C:\Users\you\NexWave\data\clean\` (keep the trailing backslash).
3. Alternatively, do this from inside Power BI Desktop after opening: **Home →
   Transform data → Edit Parameters → DataFolderPath**, then **Refresh**.

## Opening it

1. Open `NexWave Mobile.pbip` in Power BI Desktop.
2. It should load the semantic model (8 tables + the hidden `_Measures` table
   with all 21 measures) and a single blank report page.
3. Hit **Refresh** so the tables actually pull data from your `DataFolderPath`.
4. Build the 3 report pages per `docs/05_dashboard_spec.md`.

## Manual steps you still need to do

Just the `DataFolderPath` edit above. Everything else — including marking
`dim_date` as the model's Date Table (`dataCategory: Time` on the table,
`isKey` on its `date` column — the exact TOM properties Desktop's "Mark as
Date Table" action sets) — is already baked into the TMDL, so every
time-intelligence measure (YoY, MoM, YTD, trailing periods) should work as
soon as the model refreshes. `dim_date` is a genuine contiguous daily
calendar with no gaps or duplicates (2023-07-01 → 2025-12-31, verified during
Phase 2), which is what that refresh-time validation actually checks.

## How this was checked (and what wasn't)

I don't have Power BI Desktop, so I could not open this file myself. What I
did instead:

- **Schema cross-check**: a validation pass (`generate_semantic_model.py`,
  run automatically before writing any files) confirms every relationship and
  every measure's column/measure references resolve against the actual
  declared table/column list — no typos in table or column names.
- **Structural checks**: every `.tmdl` file uses consistent tab indentation,
  every DAX code block has balanced backticks and balanced
  parentheses/brackets, and every `.json` file (`.pbip`, `.pbism`, `.pbir`,
  `.platform`, `report.json`) parses as valid JSON.
- **What this does NOT guarantee**: that Power BI Desktop's TMDL parser
  accepts every property exactly as written, or that the minimal report shell
  opens without needing a small repair. If Desktop reports an issue on open,
  it's most likely to be in the `.Report` folder (the part I have the least
  confidence in) rather than the `.SemanticModel` folder (tables, relationships,
  measures — the part I'm confident about). If the Report shell doesn't open
  cleanly, delete the `NexWave Mobile.Report` folder and the `.pbip` file, then
  in Power BI Desktop use **File → Open → browse to the
  `NexWave Mobile.SemanticModel` folder** to open the model directly and let
  Desktop create a fresh connected report for you — the model itself is
  unaffected either way.

If anything doesn't open cleanly, tell me what error Power BI Desktop shows
and I'll fix the generator and regenerate.
