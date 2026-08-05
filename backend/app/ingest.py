"""Parse an uploaded TV / Radio / Press export and aggregate it.

Media type is auto-detected from the columns present:
    - has a "Channel" column  -> Radio   (no per-spot Brand; brand = mother brand)
    - has a "Dur(secs)" column -> TV
    - has an "Ins" column      -> Press   (insertions, no duration/freq)
"""
import io
import re
from collections import defaultdict

import openpyxl

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _num(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("(", "-").replace(")", "").strip()
    if s in ("", "-", "."):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_month(v) -> str | None:
    """'Jun-26' / 'Jul-2026' -> 'YYYY-MM'."""
    if v is None:
        return None
    s = str(v).strip()
    m = re.match(r"([A-Za-z]{3,})[\s\-/]+(\d{2,4})", s)
    if not m:
        return None
    mon = MONTHS.get(m.group(1)[:3].lower())
    if not mon:
        return None
    yr = int(m.group(2))
    if yr < 100:
        yr += 2000
    return f"{yr:04d}-{mon:02d}"


# Map many possible header spellings to canonical field names.
HEADER_ALIASES = {
    "month": "month",
    "product group": "product_group",
    "productgroup": "product_group",
    "category": "product_group",
    "mother brand": "mother_brand",
    "motherbrand": "mother_brand",
    "advertiser": "advertiser",
    "brand": "brand",
    "theme": "theme",
    "channel": "channel",
    "publication": "publication",
    "(000rs)": "spend",
    "000rs": "spend",
    "spend": "spend",
    "frq": "freq",
    "freq": "freq",
    "dur(secs)": "duration",
    "dur (secs)": "duration",
    "duration": "duration",
    "ins": "insertions",
    "insertions": "insertions",
}


def _find_header_row(ws):
    for r in range(1, min(ws.max_row, 15) + 1):
        vals = [_norm(ws.cell(row=r, column=c).value) for c in range(1, ws.max_column + 1)]
        if "month" in vals and any(v in ("product group", "category") for v in vals):
            return r, vals
    return None, None


def parse_workbook(content: bytes):
    """Return (media_type, aggregates, months, categories, row_count, warnings).

    `aggregates` is a dict keyed by
        (category, mother_brand, brand, theme_raw, month)
    -> {spend, freq, duration, insertions}
    """
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    ws = wb.active
    hdr_row, hdr_vals = _find_header_row(ws)
    if hdr_row is None:
        raise ValueError(
            "Could not find a header row containing 'Month' and 'Product Group'."
        )

    col_map = {}  # field -> column index (1-based)
    for idx, name in enumerate(hdr_vals, start=1):
        field = HEADER_ALIASES.get(name)
        if field and field not in col_map:
            col_map[field] = idx

    if "month" not in col_map:
        raise ValueError("No 'Month' column found.")

    # Detect media type.
    if "channel" in col_map:
        media_type = "radio"
    elif "insertions" in col_map:
        media_type = "press"
    elif "duration" in col_map:
        media_type = "tv"
    else:
        raise ValueError(
            "Could not detect media type. Expected a Channel (radio), "
            "Dur(secs) (TV) or Ins (press) column."
        )

    aggs = defaultdict(lambda: {"spend": 0.0, "freq": 0, "duration": 0, "insertions": 0})
    months, categories = set(), set()
    warnings = []
    row_count = 0

    def cell(row, field):
        c = col_map.get(field)
        return ws.cell(row=row, column=c).value if c else None

    for r in range(hdr_row + 1, ws.max_row + 1):
        month = _parse_month(cell(r, "month"))
        if not month:
            continue
        category = (str(cell(r, "product_group") or "").strip()) or "Uncategorised"
        mother = (str(cell(r, "mother_brand") or "").strip()) or (
            str(cell(r, "advertiser") or "").strip()
        )
        if not mother:
            continue
        # Radio feed has no per-spot Brand -> brand defaults to the mother brand.
        brand = (str(cell(r, "brand") or "").strip()) or mother
        theme = str(cell(r, "theme") or "").strip()
        if not theme:
            # Press feeds have no Theme column; use the Publication as the label.
            theme = str(cell(r, "publication") or "").strip() or "(no theme)"

        key = (category, mother, brand, theme, month)
        a = aggs[key]
        a["spend"] += _num(cell(r, "spend"))
        a["freq"] += int(_num(cell(r, "freq")))
        a["duration"] += int(_num(cell(r, "duration")))
        a["insertions"] += int(_num(cell(r, "insertions")))

        months.add(month)
        categories.add(category)
        row_count += 1

    wb.close()
    if row_count == 0:
        warnings.append("No data rows were parsed from the file.")
    return media_type, aggs, sorted(months), sorted(categories), row_count, warnings
