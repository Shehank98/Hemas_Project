"""Read/write global settings (VA keywords, sub-category map, financial year...).

Settings are stored one-per-key as JSON text in the `settings` table. This module
centralises the keys and their defaults so the rest of the app never guesses.
"""
import json

from sqlalchemy.orm import Session

from .models import Setting

DEFAULTS = {
    # Financial year starts in April (month index 4). YTD / column order use this.
    "fy_start_month": 4,
    # A theme is a Value-Add (bonus / free exposure) if its edited text contains
    # any of these (case-insensitive substring match).
    "va_keywords": ["Tag", "Value Add", "Value Adds", "DJ", "Scroll", "Bumper",
                    "Astons", "Crawler", "Squeeze", "L-Band"],
    # Of the VA themes, those matching this keyword go into the dedicated "Tag"
    # row; every other VA theme is summed into the "Value Adds" row.
    "tag_keyword": "Tag",
    # Brand -> Sub-category (drives column A grouping). {"Baby Cheramy": "Premium"}
    "brand_subcategory": {},
    # Optional Brand -> Mother Brand override (when the raw feed groups oddly).
    "mother_brand_map": {},
    # Optional display alias for a mother brand. {"GOYA": "Goya"}
    "mother_brand_alias": {},
}


def get_all(db: Session) -> dict:
    out = dict(DEFAULTS)
    for row in db.query(Setting).all():
        try:
            out[row.key] = json.loads(row.value)
        except (ValueError, TypeError):
            out[row.key] = row.value
    return out


def get(db: Session, key: str):
    row = db.get(Setting, key)
    if row is None:
        return DEFAULTS.get(key)
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return row.value


def set_many(db: Session, values: dict) -> None:
    for key, val in values.items():
        row = db.get(Setting, key)
        payload = json.dumps(val)
        if row is None:
            db.add(Setting(key=key, value=payload))
        else:
            row.value = payload
    db.commit()
