"""Build the summary report structure from stored facts + settings.

This is the single source of truth consumed by BOTH the API (for the UI table)
and the Excel exporter, so what you see on screen always matches the download.
"""
import calendar
import re
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from . import settings_store
from .models import BrandRef, Fact, MonthStatus, ThemeEdit

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# Normalise every dash variant (em —, en –, figure ‒, horizontal ―, minus −)
# to a plain hyphen so VA matching and display are consistent.
_DASHES = {"—": "-", "–": "-", "‒": "-", "―": "-", "−": "-"}


def clean_text(s: str) -> str:
    """Normalise dash variants to a plain hyphen (keeps spacing for display)."""
    if not s:
        return s
    for bad, good in _DASHES.items():
        s = s.replace(bad, good)
    return s


def match_norm(s: str) -> str:
    """Lower-case + collapse spacing around hyphens, so a VA name like '-BB'
    matches ' - BB', '—BB' or '– BB' regardless of dashes/spaces."""
    s = clean_text(s or "").lower()
    return re.sub(r"\s*-\s*", "-", s)


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def fy_of_month(month_key: str, fy_start: int) -> int:
    """Return the financial-year start year for a YYYY-MM month."""
    y, m = int(month_key[:4]), int(month_key[5:7])
    return y if m >= fy_start else y - 1


def fy_month_keys(fy_start_year: int, fy_start: int) -> list[str]:
    keys = []
    for i in range(12):
        m = (fy_start - 1 + i) % 12 + 1
        y = fy_start_year + (1 if m < fy_start else 0)
        keys.append(f"{y:04d}-{m:02d}")
    return keys


def fy_label(fy_start_year: int, fy_start: int = 4) -> str:
    # Calendar year (Jan start) -> "2026"; otherwise a split year -> "2026-27".
    if fy_start == 1:
        return f"{fy_start_year}"
    return f"{fy_start_year}-{str(fy_start_year + 1)[-2:]}"


def list_categories(db: Session) -> list[str]:
    rows = db.query(Fact.category).distinct().all()
    return sorted(r[0] for r in rows)


def available_fys(db: Session, category: str, fy_start: int) -> list[int]:
    rows = db.query(Fact.month).filter(Fact.category == category).distinct().all()
    return sorted({fy_of_month(r[0], fy_start) for r in rows}, reverse=True)


def _classify(text: str, va_theme_set, va_keywords, tag_keyword) -> str:
    low = match_norm(text)
    if tag_keyword and match_norm(tag_keyword) in low:
        return "tag"
    if low in va_theme_set:  # exact theme picked in Settings
        return "va"
    for kw in va_keywords:  # optional substring fallback
        if kw and match_norm(kw) in low:
            return "va"
    return "commercial"


def _acd(monthly_dur, monthly_freq, keys):
    """ACD per month = sum(duration) / sum(freq); None where freq is 0."""
    out, tot_d, tot_f = {}, 0, 0
    for k in keys:
        d, f = monthly_dur.get(k, 0), monthly_freq.get(k, 0)
        out[k] = (d / f) if f else None
        tot_d += d
        tot_f += f
    out["ytd"] = (tot_d / tot_f) if tot_f else None
    return out


def _sum_row(monthly, keys):
    out = {k: monthly.get(k, 0.0) for k in keys}
    out["ytd"] = sum(monthly.get(k, 0.0) for k in keys)
    return out


def build_summary(db: Session, category: str, fy_start_year: int | None = None) -> dict:
    cfg = settings_store.get_all(db)
    fy_start = int(cfg.get("fy_start_month", 4))
    va_keywords = cfg.get("va_keywords", [])
    va_theme_set = {match_norm(t) for t in cfg.get("va_themes", []) if t}
    tag_keyword = cfg.get("tag_keyword", "Tag")
    brand_subcat = cfg.get("brand_subcategory", {})
    mb_alias = cfg.get("mother_brand_alias", {})

    fys = available_fys(db, category, fy_start)
    if fy_start_year is None:
        fy_start_year = fys[0] if fys else fy_of_month(
            date.today().strftime("%Y-%m"), fy_start
        )
    # Always show the whole financial year, April through March (no breaks).
    keys = fy_month_keys(fy_start_year, fy_start)
    keyset = set(keys)
    all_months = {
        r[0]
        for r in db.query(Fact.month).filter(Fact.category == category).distinct()
    }

    # --- theme edits + month status + brand refs ---
    edits = {
        e.theme_raw: e.edit_text
        for e in db.query(ThemeEdit).filter(ThemeEdit.category == category)
    }
    mstatus = {
        m.month: m
        for m in db.query(MonthStatus).filter(MonthStatus.category == category)
    }
    refs = {
        r.brand: r
        for r in db.query(BrandRef).filter(BrandRef.category == category)
    }

    facts = (
        db.query(Fact)
        .filter(Fact.category == category, Fact.month.in_(keys))
        .all()
    )
    months_with_data = all_months

    # --- month headers (partial vs complete) ---
    months_meta = []
    for k in keys:
        y, m = int(k[:4]), int(k[5:7])
        name = MONTH_NAMES[m]
        st = mstatus.get(k)
        has_data = k in months_with_data
        later_data = any(mk > k for mk in months_with_data)
        if st and st.complete_override is not None:
            complete = st.complete_override
        else:
            as_of = st.as_of_date if st else None
            month_end = date(y, m, calendar.monthrange(y, m)[1])
            complete = (as_of is not None and as_of >= month_end) or later_data
        partial = has_data and not complete
        header = name
        as_of_day = None
        if partial and st and st.as_of_date:
            as_of_day = st.as_of_date.day
            header = f"1st to {_ordinal(as_of_day)} {name}"
        months_meta.append({
            "key": k, "name": name, "header": header,
            "complete": complete, "partial": partial,
            "has_data": has_data, "as_of_day": as_of_day,
            "override": st.complete_override if st else None,
        })

    # --- nest facts: mother -> brand -> theme_edit -> monthly numbers/bucket ---
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(
        lambda: {"spend": defaultdict(float), "freq": defaultdict(int),
                 "dur": defaultdict(int)}
    )))
    for f in facts:
        if f.month not in keyset:
            continue
        edit = clean_text(edits.get(f.theme_raw, f.theme_raw)).strip() or f.theme_raw
        node = tree[f.mother_brand][f.brand][edit]
        node["spend"][f.month] += f.spend
        node["freq"][f.month] += f.freq
        node["dur"][f.month] += f.duration

    groups = []
    category_total = defaultdict(float)
    sos = []

    for mother in sorted(tree.keys()):
        brands_node = tree[mother]
        mb_display = mb_alias.get(mother, mother)
        subcat = ""
        brands_out = []
        mb_total = defaultdict(float)
        mb_dur_all = defaultdict(int)
        mb_freq_all = defaultdict(int)
        mb_mont_avg = 0.0
        mb_weekly_avg = 0.0

        for brand in sorted(brands_node.keys()):
            themes_node = brands_node[brand]
            if brand in brand_subcat and not subcat:
                subcat = brand_subcat[brand]
            themes_out = []
            tag_spend = defaultdict(float)
            va_spend = defaultdict(float)
            com_dur = defaultdict(int)
            com_freq = defaultdict(int)
            all_dur = defaultdict(int)
            all_freq = defaultdict(int)
            brand_total = defaultdict(float)

            for text in sorted(themes_node.keys()):
                node = themes_node[text]
                bucket = _classify(text, va_theme_set, va_keywords, tag_keyword)
                for k in keys:
                    sp = node["spend"].get(k, 0.0)
                    fr = node["freq"].get(k, 0)
                    du = node["dur"].get(k, 0)
                    brand_total[k] += sp
                    all_dur[k] += du
                    all_freq[k] += fr
                    if bucket == "tag":
                        tag_spend[k] += sp
                    elif bucket == "va":
                        va_spend[k] += sp
                    else:
                        com_dur[k] += du
                        com_freq[k] += fr
                if bucket == "commercial":
                    themes_out.append({"text": text, **_sum_row(node["spend"], keys)})

            ref = refs.get(brand)
            mont_avg = ref.mont_avg if ref and ref.mont_avg is not None else None
            weekly_avg = ref.weekly_avg if ref and ref.weekly_avg is not None else None
            mb_mont_avg += mont_avg or 0.0
            mb_weekly_avg += weekly_avg or 0.0

            for k in keys:
                mb_total[k] += brand_total[k]
                mb_dur_all[k] += all_dur[k]
                mb_freq_all[k] += all_freq[k]

            brands_out.append({
                "brand": brand,
                "mont_avg": mont_avg,
                "weekly_avg": weekly_avg,
                "themes": themes_out,
                "tag": _sum_row(tag_spend, keys),
                "value_adds": _sum_row(va_spend, keys),
                "total": _sum_row(brand_total, keys),
                "acd_com": _acd(com_dur, com_freq, keys),
                "acd_all": _acd(all_dur, all_freq, keys),
                "has_tag": any(tag_spend.values()),
            })

        for k in keys:
            category_total[k] += mb_total[k]

        groups.append({
            "mother_brand": mb_display,
            "subcategory": subcat,
            "show_total": len(brands_out) > 1,
            "brands": brands_out,
            "total": {**_sum_row(mb_total, keys),
                      "mont_avg": mb_mont_avg or None,
                      "weekly_avg": mb_weekly_avg or None},
            "total_acd": _acd(mb_dur_all, mb_freq_all, keys),
            "_mb_total": dict(mb_total),
        })

    cat_total_row = _sum_row(category_total, keys)
    for g in groups:
        mb_total = g.pop("_mb_total")
        srow = {}
        for k in keys:
            ct = category_total.get(k, 0.0)
            srow[k] = (mb_total.get(k, 0.0) / ct) if ct else None
        ytd_ct = cat_total_row["ytd"]
        srow["ytd"] = (g["total"]["ytd"] / ytd_ct) if ytd_ct else None
        sos.append({"mother_brand": g["mother_brand"], **srow})

    return {
        "category": category,
        "fy": fy_label(fy_start_year, fy_start),
        "fy_start_year": fy_start_year,
        "available_fys": [fy_label(y, fy_start) for y in fys],
        "available_fy_years": fys,
        "month_keys": keys,
        "months": months_meta,
        "groups": groups,
        "category_total": cat_total_row,
        "sos": sos,
    }
