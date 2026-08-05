# Media Tracking Dashboard

Upload monthly **TV**, **Radio** and **Press** advertising exports, and the app
builds the per–product-group "Asset Update" summary automatically — spend by
brand and commercial, value-adds, ACD, Share-of-Spend — viewable in the browser
and exportable to Excel that mirrors the existing template.

Built for [Hemas] media tracking. Deploys as a single service on **Railway**
with **Postgres**.

---

## What it does

1. **Upload** a TV / Radio / Press `.xlsx` export. The media type is auto-detected
   from the columns. You pick an **as-of date** ("data is complete up to…").
2. Raw rows are **aggregated and only the numbers are stored** — one number-set
   per `(product group, mother brand, brand, theme, media, month)`. Millions of
   raw spot rows never touch the database, so storage stays tiny.
3. The **Dashboard** renders the summary for any product group / financial year:
   brand blocks, `Tag` / `Value Adds`, `Total Spends (000)`, `ACD (Com Only)`,
   `ACD (All Exp)`, mother-brand totals, `TOTAL CATEGORY SPEND` and `SOS %`.
4. **Export** any category (or all as a zip) to a formatted `.xlsx` matching the
   `Asset_Update` template.

### Summary year (calendar by default)

Summaries are built **per year, one sheet each**. The year runs **April–March**
(label `2026-27`); switch to a calendar year via **Summary year starts** in
Settings. Pick the year with the **Year** filter, and next year's data
automatically forms a new year's summary. **All twelve months (April→March) are
always shown**, with no breaks. The export layout matches the client template:
`CATEGORY(sub) | CATEGORY | BRAND | COMMERCIAL | 2022/23 (Mont/Weekly Avg) |
April…March | YTD`.

**Each product group is themed in its own colour** (brown, green, blue, …), so
every category's export sheet is visually distinct. The colour is stable per
category and the dashboard uses the same theme.

### Month completion & partial months

Every upload carries an as-of date. A month shows as **partial** in the header
(e.g. `1st to 14th July`) until it is complete; a complete month shows just its
name (`July`). A month auto-completes once data for a **later** month arrives, and
you can **manually** override completion by clicking a month header on the
dashboard (cycles complete → partial → auto).

### Re-uploading (cumulative feeds)

Media feeds are cumulative-to-date. Re-uploading the **same media type** for a
month **replaces** that month's numbers for that media type (e.g. TV July-to-14th
then TV July-to-20th). Other media types for the same month are untouched and add
on top — no double counting.

### Value-Adds (VA), Tag, and ACD

- In **Settings → Value-Add (VA) themes** every commercial theme in your data is
  listed with a checkbox. **Tick the themes that are value-adds** — they're grouped
  into the **Value Adds** row and excluded from ACD (Com Only). Changes apply
  instantly, no re-upload. (Matching ignores dash style/spacing, so `—BB`, `– BB`
  and ` - BB` are treated the same.)
- The dedicated **Tag** row collects VA themes matching the *Tag keyword*; all
  other VA themes roll into the **Value Adds** row. Non-VA themes list
  individually.
- **ACD (Com Only)** = Σ duration ÷ Σ frequency across **commercials only**
  (VA excluded). **ACD (All Exp)** = the same ratio across **all** exposures
  (commercials + VA). Press has no duration/frequency, so it never affects ACD.

### Sub-category & theme editing

- **Brand → Sub-category** mapping (Settings) drives column A grouping.
- **Theme editing** (Settings) lets you rename a theme's display text; themes
  sharing the same edited text within a brand **merge** into one row.
- **Reference columns** (`Mont Avg Spend`, `Weekly Avg Spend`) are maintained by
  hand per brand in Settings.

---

## Architecture

```
frontend/  React + Vite SPA (Dashboard, Upload, Settings)
backend/   FastAPI + SQLAlchemy
           app/ingest.py        parse & detect TV/Radio/Press, aggregate
           app/summary.py       build the report structure (VA, ACD, SOS, months)
           app/excel_export.py  openpyxl export matching the template
           app/main.py          API + serves the built frontend
```

The frontend build is emitted into `backend/app/static` and served by FastAPI, so
the whole thing runs as **one** Railway service.

### Data model (only numbers stored)

| Table          | Purpose                                                        |
|----------------|----------------------------------------------------------------|
| `facts`        | aggregated spend/freq/duration/insertions per key (the numbers)|
| `upload_batches`| audit of each upload (media, as-of date, months, filename)    |
| `theme_edits`  | per-category theme display-text overrides                      |
| `month_status` | per (category, month) as-of date + completion override         |
| `brand_refs`   | manual Mont/Weekly average reference values                    |
| `settings`     | VA keywords, tag keyword, sub-category map, FY start, aliases   |

---

## Local development

**Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # uses SQLite if DATABASE_URL unset
```

**Frontend** (separate terminal, proxies /api to :8000)
```bash
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

Or build the frontend and let the backend serve it:
```bash
cd frontend && npm run build                  # outputs to ../backend/app/static
cd ../backend && uvicorn app.main:app --port 8000   # open http://localhost:8000
```

---

## Deploy to Railway

1. Create a new Railway project from this repo. Railway detects the `Dockerfile`.
2. Add the **Postgres** plugin. Railway injects `DATABASE_URL` automatically —
   the app picks it up (and normalises `postgres://` → the psycopg driver).
3. Deploy. Tables are created on first boot. `PORT` is provided by Railway.

No other configuration is required.

---

## Expected upload columns

| Media | Columns |
|-------|---------|
| TV    | Month, Product Group, Mother Brand, Advertiser, Brand, Theme, (000Rs), Frq, Dur(secs) |
| Radio | Month, Product Group, Mother Brand, Advertiser, Theme, Channel, (000Rs), Frq, Dur(secs) |
| Press | Month, Product Group, Mother Brand, Advertiser, Brand, Publication, (000Rs), Ins |

Header spellings are matched loosely (extra spaces / casing are fine). `Month`
accepts `Jun-26`, `Jul-2026`, etc.
