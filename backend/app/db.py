"""Database engine / session setup.

Uses Postgres when DATABASE_URL is provided (Railway), otherwise falls back to a
local SQLite file so the app runs anywhere for development.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _normalize_url(url: str) -> str:
    # Railway / Heroku style "postgres://" -> SQLAlchemy + psycopg3 driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    ENGINE_URL = _normalize_url(DATABASE_URL)
    connect_args = {}
else:
    ENGINE_URL = "sqlite:///./media_tracking.db"
    connect_args = {"check_same_thread": False}

engine = create_engine(ENGINE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
