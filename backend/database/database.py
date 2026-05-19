# ============================================================
# EXACT FILE LOCATION: backend/database/database.py
# ============================================================
# UPDATED — Added run_migrations() to safely add new columns
# to existing SQLite tables without losing any data.
#
# SQLAlchemy's create_all() only creates MISSING tables.
# It never adds columns to tables that already exist.
# run_migrations() fills that gap using raw ALTER TABLE.
# ============================================================

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging
import os

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./screening.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# run_migrations
# ============================================================
# Adds missing columns to existing tables.
# Each migration is wrapped in its own try/except so one
# failure never blocks the rest.
#
# Pattern for every migration:
#   ALTER TABLE <table> ADD COLUMN <col> <type> <default>
#
# SQLite ignores "ADD COLUMN IF NOT EXISTS" in older versions,
# so we catch the OperationalError that fires when the column
# already exists and move on silently.
# ============================================================
def run_migrations():
    migrations = [
        # ── Phase 5 additions to candidates table ──────────
        (
            "candidates.match_percentage",
            "ALTER TABLE candidates ADD COLUMN match_percentage REAL"
        ),
        # ── Phase 6/7/8 additions — interview tables are new
        # so no ALTER needed; create_all() handles them.
        # Add future column migrations here in the same format.
    ]

    with engine.connect() as conn:
        for migration_name, sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"Migration applied: {migration_name}")
            except Exception as e:
                # Column already exists — safe to ignore
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    logger.debug(f"Migration skipped (already exists): {migration_name}")
                else:
                    logger.warning(f"Migration '{migration_name}' skipped: {e}")


# ============================================================
# init_db
# 1. Imports all models so SQLAlchemy registers their tables
# 2. Creates any MISSING tables (safe to run every startup)
# 3. Runs column migrations for existing tables
# ============================================================
def init_db():
    from models import job, candidate          # Phase 1
    from models import application             # Phase 2
    from models import ai_models               # Phase 3/4/5
    from models import interview_models        # Phase 6/7/8

    # Create all tables that do not yet exist
    Base.metadata.create_all(bind=engine)

    # Add any new columns to existing tables
    run_migrations()

    logger.info("Database initialized and migrations applied")