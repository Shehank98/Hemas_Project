"""FastAPI application: uploads, settings, summary view and Excel export.

Serves the built React frontend as static files (single Railway service).
"""
import io
import os
import zipfile
from datetime import date, datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from . import settings_store, summary
from .db import Base, engine, get_db
from .excel_export import build_workbook
from .ingest import parse_workbook
from .models import BrandRef, Fact, MonthStatus, ThemeEdit, UploadBatch

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Media Tracking Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip()


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #
@app.post("/api/upload/preview")
async def upload_preview(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        media_type, aggs, months, categories, row_count, warnings = parse_workbook(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Which (category, month) already have data for this media type (would be replaced)?
    pairs = {(c, m) for (c, _mb, _b, _t, m) in aggs.keys()}
    replacements = []
    for cat, month in sorted(pairs):
        existing = (
            db.query(Fact)
            .filter(Fact.category == cat, Fact.month == month,
                    Fact.media_type == media_type)
            .count()
        )
        if existing:
            replacements.append({"category": cat, "month": month, "existing_rows": existing})

    total_spend = sum(a["spend"] for a in aggs.values())
    return {
        "media_type": media_type,
        "months": months,
        "categories": categories,
        "row_count": row_count,
        "aggregated_rows": len(aggs),
        "total_spend": round(total_spend, 2),
        "replacements": replacements,
        "warnings": warnings,
    }


@app.post("/api/upload/commit")
async def upload_commit(
    file: UploadFile = File(...),
    as_of_date: str = Form(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        media_type, aggs, months, categories, row_count, warnings = parse_workbook(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD")

    # Replace semantics: for every (category, month) in this file, clear the
    # previous numbers for THIS media type, then insert the fresh aggregates.
    pairs = {(c, m) for (c, _mb, _b, _t, m) in aggs.keys()}
    for cat, month in pairs:
        db.query(Fact).filter(
            Fact.category == cat, Fact.month == month, Fact.media_type == media_type
        ).delete(synchronize_session=False)

    for (cat, mother, brand, theme, month), v in aggs.items():
        db.add(Fact(
            category=cat, mother_brand=mother, brand=brand, theme_raw=theme,
            media_type=media_type, month=month,
            spend=v["spend"], freq=v["freq"], duration=v["duration"],
            insertions=v["insertions"],
        ))

    # Update month status (latest as-of date wins).
    for cat, month in pairs:
        st = (
            db.query(MonthStatus)
            .filter(MonthStatus.category == cat, MonthStatus.month == month)
            .first()
        )
        if st is None:
            db.add(MonthStatus(category=cat, month=month, as_of_date=as_of))
        elif st.as_of_date is None or as_of >= st.as_of_date:
            st.as_of_date = as_of

    db.add(UploadBatch(
        filename=file.filename or "upload.xlsx",
        media_type=media_type,
        as_of_date=as_of,
        categories=",".join(sorted(categories)),
        months=",".join(sorted(months)),
        row_count=row_count,
    ))
    db.commit()
    return {
        "ok": True,
        "media_type": media_type,
        "categories": sorted(categories),
        "months": sorted(months),
        "rows_stored": len(aggs),
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# Summary / view
# --------------------------------------------------------------------------- #
@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    return {"categories": summary.list_categories(db)}


@app.get("/api/summary")
def get_summary(category: str, fy: int | None = None, db: Session = Depends(get_db)):
    from .excel_export import palette_for
    cats = summary.list_categories(db)
    if category not in cats:
        raise HTTPException(status_code=404, detail="Unknown category")
    out = summary.build_summary(db, category, fy)
    out["palette"] = palette_for(cats.index(category))
    return out


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def _color_index(db, category) -> int:
    """Stable colour slot for a category (its position in the sorted list)."""
    cats = summary.list_categories(db)
    return cats.index(category) if category in cats else 0


def _workbook_for_category(db, category, fy=None, color_index=0) -> bytes:
    cfg = settings_store.get_all(db)
    fy_start = int(cfg.get("fy_start_month", 4))
    if fy is not None:
        summaries = [summary.build_summary(db, category, fy)]
    else:
        years = summary.available_fys(db, category, fy_start) or [None]
        summaries = [summary.build_summary(db, category, y) for y in years]
    return build_workbook(summaries, color_index=color_index)


@app.get("/api/export")
def export_category(category: str, fy: int | None = None, db: Session = Depends(get_db)):
    if category not in summary.list_categories(db):
        raise HTTPException(status_code=404, detail="Unknown category")
    data = _workbook_for_category(db, category, fy, _color_index(db, category))
    fname = f"Asset_Update__{_safe_name(category)}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/export_all")
def export_all(db: Session = Depends(get_db)):
    cats = summary.list_categories(db)
    if not cats:
        raise HTTPException(status_code=404, detail="No data to export")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, cat in enumerate(cats):
            data = _workbook_for_category(db, cat, color_index=idx)
            zf.writestr(f"Asset_Update__{_safe_name(cat)}.xlsx", data)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="media_summaries.zip"'},
    )


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    return settings_store.get_all(db)


@app.put("/api/settings")
def put_settings(payload: dict, db: Session = Depends(get_db)):
    allowed = set(settings_store.DEFAULTS.keys())
    clean = {k: v for k, v in payload.items() if k in allowed}
    settings_store.set_many(db, clean)
    return settings_store.get_all(db)


# --------------------------------------------------------------------------- #
# Brands / themes helpers for settings screens
# --------------------------------------------------------------------------- #
@app.get("/api/brands")
def get_brands(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(distinct(Fact.brand))
    if category:
        q = q.filter(Fact.category == category)
    brands = sorted(r[0] for r in q.all())
    q2 = db.query(distinct(Fact.mother_brand))
    if category:
        q2 = q2.filter(Fact.category == category)
    mothers = sorted(r[0] for r in q2.all())
    return {"brands": brands, "mother_brands": mothers}


@app.get("/api/all-themes")
def get_all_themes(db: Session = Depends(get_db)):
    """Every distinct commercial theme across all categories, for the VA picker."""
    rows = (
        db.query(Fact.theme_raw, Fact.brand, Fact.category)
        .distinct()
        .all()
    )
    seen = {}
    for theme, brand, cat in rows:
        if theme not in seen:
            seen[theme] = {"theme_raw": theme, "brand": brand, "category": cat}
    themes = sorted(seen.values(), key=lambda x: x["theme_raw"].lower())
    return {"themes": themes}


@app.get("/api/themes")
def get_themes(category: str, db: Session = Depends(get_db)):
    edits = {
        e.theme_raw: e.edit_text
        for e in db.query(ThemeEdit).filter(ThemeEdit.category == category)
    }
    rows = (
        db.query(Fact.brand, Fact.theme_raw)
        .filter(Fact.category == category)
        .distinct()
        .all()
    )
    seen = {}
    for brand, theme in rows:
        seen.setdefault(theme, brand)
    themes = [
        {"theme_raw": t, "brand": b, "edit_text": edits.get(t, t)}
        for t, b in sorted(seen.items())
    ]
    return {"themes": themes}


@app.put("/api/theme-edits")
def put_theme_edits(payload: dict, db: Session = Depends(get_db)):
    category = payload.get("category")
    if not category:
        raise HTTPException(status_code=400, detail="category required")
    for item in payload.get("edits", []):
        raw = item.get("theme_raw")
        text = (item.get("edit_text") or "").strip()
        if not raw:
            continue
        row = (
            db.query(ThemeEdit)
            .filter(ThemeEdit.category == category, ThemeEdit.theme_raw == raw)
            .first()
        )
        if not text or text == raw:
            if row:
                db.delete(row)
            continue
        if row:
            row.edit_text = text
        else:
            db.add(ThemeEdit(category=category, theme_raw=raw, edit_text=text))
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Month status + brand reference columns
# --------------------------------------------------------------------------- #
@app.get("/api/month-status")
def get_month_status(category: str, db: Session = Depends(get_db)):
    rows = db.query(MonthStatus).filter(MonthStatus.category == category).all()
    return {
        "months": [
            {
                "month": r.month,
                "as_of_date": r.as_of_date.isoformat() if r.as_of_date else None,
                "complete_override": r.complete_override,
            }
            for r in sorted(rows, key=lambda x: x.month)
        ]
    }


@app.put("/api/month-status")
def put_month_status(payload: dict, db: Session = Depends(get_db)):
    category = payload.get("category")
    month = payload.get("month")
    if not category or not month:
        raise HTTPException(status_code=400, detail="category and month required")
    row = (
        db.query(MonthStatus)
        .filter(MonthStatus.category == category, MonthStatus.month == month)
        .first()
    )
    if row is None:
        row = MonthStatus(category=category, month=month)
        db.add(row)
    if "complete_override" in payload:
        val = payload["complete_override"]
        row.complete_override = None if val is None else bool(val)
    if payload.get("as_of_date"):
        row.as_of_date = datetime.strptime(payload["as_of_date"], "%Y-%m-%d").date()
    db.commit()
    return {"ok": True}


@app.get("/api/brand-refs")
def get_brand_refs(category: str, db: Session = Depends(get_db)):
    rows = db.query(BrandRef).filter(BrandRef.category == category).all()
    return {
        "refs": [
            {"brand": r.brand, "mont_avg": r.mont_avg, "weekly_avg": r.weekly_avg}
            for r in rows
        ]
    }


@app.put("/api/brand-refs")
def put_brand_refs(payload: dict, db: Session = Depends(get_db)):
    category = payload.get("category")
    if not category:
        raise HTTPException(status_code=400, detail="category required")
    for item in payload.get("refs", []):
        brand = item.get("brand")
        if not brand:
            continue
        row = (
            db.query(BrandRef)
            .filter(BrandRef.category == category, BrandRef.brand == brand)
            .first()
        )
        if row is None:
            row = BrandRef(category=category, brand=brand)
            db.add(row)
        row.mont_avg = item.get("mont_avg")
        row.weekly_avg = item.get("weekly_avg")
    db.commit()
    return {"ok": True}


@app.get("/api/health")
def health():
    from .db import ENGINE_URL
    backend = "postgres" if "postgresql" in ENGINE_URL else "sqlite"
    return {
        "status": "ok",
        "database": backend,
        "persistent": backend == "postgres",
    }


# --------------------------------------------------------------------------- #
# Static frontend (built React app)
# --------------------------------------------------------------------------- #
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")),
              name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = os.path.join(_STATIC_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
