"""SQLAlchemy models.

Design note: raw upload rows are NOT stored. During ingestion we aggregate the
raw rows down to one number-set per
    (category, mother_brand, brand, theme_raw, media_type, month)
and only those aggregates live in the `facts` table. That is enough to rebuild
every summary (spend, ACD, SOS, value-adds) without keeping millions of rows.
"""
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Fact(Base):
    """One aggregated number-set per theme / media / month."""

    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint(
            "category",
            "mother_brand",
            "brand",
            "theme_raw",
            "media_type",
            "month",
            name="uq_fact_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The upload that produced this aggregated row (for delete/undo).
    batch_id: Mapped[int] = mapped_column(Integer, index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(200), index=True)  # product group
    mother_brand: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[str] = mapped_column(String(200), index=True)
    theme_raw: Mapped[str] = mapped_column(String(600))
    media_type: Mapped[str] = mapped_column(String(10))  # tv | radio | press
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM

    spend: Mapped[float] = mapped_column(Float, default=0.0)  # in 000 Rs
    freq: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[int] = mapped_column(Integer, default=0)  # seconds
    insertions: Mapped[int] = mapped_column(Integer, default=0)


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(400))
    media_type: Mapped[str] = mapped_column(String(10))
    as_of_date: Mapped[date] = mapped_column(Date)
    categories: Mapped[str] = mapped_column(String(2000), default="")  # csv
    months: Mapped[str] = mapped_column(String(2000), default="")  # csv YYYY-MM
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ThemeEdit(Base):
    """User override of the display text for a raw theme (per category)."""

    __tablename__ = "theme_edits"
    __table_args__ = (
        UniqueConstraint("category", "theme_raw", name="uq_theme_edit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(200), index=True)
    theme_raw: Mapped[str] = mapped_column(String(600))
    edit_text: Mapped[str] = mapped_column(String(600))


class MonthStatus(Base):
    """Per (category, month) completion state + latest as-of date."""

    __tablename__ = "month_status"
    __table_args__ = (
        UniqueConstraint("category", "month", name="uq_month_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(200), index=True)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    as_of_date: Mapped[date] = mapped_column(Date, nullable=True)
    # None = auto, True/False = manual override
    complete_override: Mapped[bool] = mapped_column(Boolean, nullable=True)


class BrandRef(Base):
    """Manually maintained reference columns (E/F in the summary)."""

    __tablename__ = "brand_refs"
    __table_args__ = (
        UniqueConstraint("category", "brand", name="uq_brand_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[str] = mapped_column(String(200))
    mont_avg: Mapped[float] = mapped_column(Float, nullable=True)
    weekly_avg: Mapped[float] = mapped_column(Float, nullable=True)


class Setting(Base):
    """Global key/value settings stored as JSON text."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String, default="")
