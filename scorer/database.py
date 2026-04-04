"""
Database layer — SQLAlchemy models + query functions.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    create_engine,
    desc,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/subnet_scores.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class SubnetScoreRow(Base):
    __tablename__ = "subnet_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    netuid = Column(Integer, nullable=False, index=True)
    score = Column(Float, nullable=False)
    capital_score = Column(Float, nullable=False)
    activity_score = Column(Float, nullable=False)
    efficiency_score = Column(Float, nullable=False)
    health_score = Column(Float, nullable=False)
    dev_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    score_version = Column(String(64), nullable=False, default="v1")
    raw_data = Column(JSON, nullable=True)
    # dTAO market data (added v3.0)
    alpha_price_tao = Column(Float, nullable=True)
    tao_in_pool = Column(Float, nullable=True)
    market_cap_tao = Column(Float, nullable=True)
    staking_apy = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_subnet_scores_netuid_computed_at", "netuid", "computed_at"),
    )


class SubnetMetadataRow(Base):
    __tablename__ = "subnet_metadata"

    netuid = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=True)
    github_url = Column(String(512), nullable=True)
    website = Column(String(512), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=False)


class ExternalDataSnapshotRow(Base):
    __tablename__ = "external_data_snapshots"

    netuid = Column(Integer, primary_key=True)
    github_url = Column(String(512), nullable=True)
    owner = Column(String(256), nullable=True)
    repo = Column(String(256), nullable=True)
    source_status = Column(String(64), nullable=False, default="unavailable")
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    commits_30d = Column(Integer, nullable=False, default=0)
    contributors_30d = Column(Integer, nullable=False, default=0)
    commits_90d = Column(Integer, nullable=False, default=0)
    contributors_90d = Column(Integer, nullable=False, default=0)
    commits_180d = Column(Integer, nullable=False, default=0)
    contributors_180d = Column(Integer, nullable=False, default=0)
    stars = Column(Integer, nullable=False, default=0)
    forks = Column(Integer, nullable=False, default=0)
    open_issues = Column(Integer, nullable=False, default=0)
    last_push = Column(String(64), nullable=True)
    last_commit_at = Column(String(64), nullable=True)


def create_tables() -> None:
    """Create all tables and run additive migrations (idempotent)."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_dtao_columns()
    _migrate_score_version_length()
    _migrate_external_snapshot_columns()


def _migrate_add_dtao_columns() -> None:
    """Add dTAO columns to subnet_scores if they don't exist yet."""
    new_cols = [
        ("alpha_price_tao", "FLOAT"),
        ("tao_in_pool", "FLOAT"),
        ("market_cap_tao", "FLOAT"),
        ("staking_apy", "FLOAT"),
    ]
    with engine.connect() as conn:
        for col, col_type in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE subnet_scores ADD COLUMN {col} {col_type}"))
                conn.commit()
                logger.info("Migration: added column subnet_scores.%s", col)
            except Exception:
                pass  # column already exists — safe to ignore


def _migrate_score_version_length() -> None:
    """Ensure score_version can store longer model identifiers."""
    with engine.connect() as conn:
        try:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE subnet_scores ALTER COLUMN score_version TYPE VARCHAR(64)"))
                conn.commit()
        except Exception:
            pass


def _migrate_external_snapshot_columns() -> None:
    """Add newer external snapshot columns for multi-horizon repo evidence."""
    new_cols = [
        ("commits_90d", "INTEGER DEFAULT 0"),
        ("contributors_90d", "INTEGER DEFAULT 0"),
        ("commits_180d", "INTEGER DEFAULT 0"),
        ("contributors_180d", "INTEGER DEFAULT 0"),
        ("last_commit_at", "VARCHAR(64)"),
    ]
    with engine.connect() as conn:
        for col, col_type in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE external_data_snapshots ADD COLUMN {col} {col_type}"))
                conn.commit()
                logger.info("Migration: added column external_data_snapshots.%s", col)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Write functions
# ---------------------------------------------------------------------------

def save_scores(scores: list, raw_data_by_netuid: Optional[dict] = None) -> None:
    """
    Bulk-insert a list of SubnetScore objects.

    Args:
        scores: list of scorer.composite.SubnetScore
        raw_data_by_netuid: optional dict[netuid → dict] of raw API payloads
    """
    if not scores:
        return

    raw_data_by_netuid = raw_data_by_netuid or {}
    now = datetime.now(timezone.utc)

    rows = [
        SubnetScoreRow(
            netuid=s.netuid,
            score=s.score,
            capital_score=s.breakdown.capital_score,
            activity_score=s.breakdown.activity_score,
            efficiency_score=s.breakdown.efficiency_score,
            health_score=s.breakdown.health_score,
            dev_score=s.breakdown.dev_score,
            rank=s.rank,
            computed_at=now,
            score_version=s.version,
            raw_data=raw_data_by_netuid.get(s.netuid) or getattr(s, "analysis", None),
            alpha_price_tao=getattr(s, "alpha_price_tao", None) or None,
            tao_in_pool=getattr(s, "tao_in_pool", None) or None,
            market_cap_tao=getattr(s, "market_cap_tao", None) or None,
            staking_apy=getattr(s, "staking_apy", None) or None,
        )
        for s in scores
    ]

    with SessionLocal() as session:
        session.add_all(rows)
        session.commit()

    logger.info("Saved %d scores to database", len(rows))


def upsert_metadata(netuid: int, name: Optional[str], github_url: Optional[str], website: Optional[str]) -> None:
    """Insert or update a subnet's metadata row."""
    now = datetime.now(timezone.utc)
    safe_name = _sanitize_metadata_name(name, netuid)
    with SessionLocal() as session:
        row = session.get(SubnetMetadataRow, netuid)
        if row is None:
            row = SubnetMetadataRow(netuid=netuid, first_seen=now)
            session.add(row)
        row.name = safe_name
        row.github_url = github_url
        row.website = website
        row.last_updated = now
        session.commit()


def upsert_external_data_snapshot(
    *,
    netuid: int,
    github_url: Optional[str],
    owner: Optional[str],
    repo: Optional[str],
    source_status: str,
    fetched_at: datetime,
    commits_30d: int,
    contributors_30d: int,
    commits_90d: int,
    contributors_90d: int,
    commits_180d: int,
    contributors_180d: int,
    stars: int,
    forks: int,
    open_issues: int,
    last_push: Optional[str],
    last_commit_at: Optional[str],
) -> None:
    """Insert or update the latest external evidence snapshot for a subnet."""
    with SessionLocal() as session:
        row = session.get(ExternalDataSnapshotRow, netuid)
        if row is None:
            row = ExternalDataSnapshotRow(netuid=netuid)
            session.add(row)
        row.github_url = github_url
        row.owner = owner
        row.repo = repo
        row.source_status = source_status
        row.fetched_at = fetched_at
        row.commits_30d = commits_30d
        row.contributors_30d = contributors_30d
        row.commits_90d = commits_90d
        row.contributors_90d = contributors_90d
        row.commits_180d = commits_180d
        row.contributors_180d = contributors_180d
        row.stars = stars
        row.forks = forks
        row.open_issues = open_issues
        row.last_push = last_push
        row.last_commit_at = last_commit_at
        session.commit()


# ---------------------------------------------------------------------------
# Read functions
# ---------------------------------------------------------------------------

def get_all_metadata() -> dict[int, dict]:
    """Return all subnet metadata rows as a dict keyed by netuid."""
    with SessionLocal() as session:
        rows = session.execute(select(SubnetMetadataRow)).scalars().all()
    return {
        r.netuid: {
            "name": r.name,
            "github_url": r.github_url,
            "website": r.website,
            "first_seen": r.first_seen.isoformat() if r.first_seen else None,
            "last_updated": r.last_updated.isoformat() if r.last_updated else None,
        }
        for r in rows
    }


def get_latest_scores() -> list[dict]:
    """
    Return the most recent score for every subnet (one row per netuid).
    Sorted by score descending.
    """
    with SessionLocal() as session:
        # Subquery: max computed_at per netuid
        latest_sub = (
            select(
                SubnetScoreRow.netuid,
                func.max(SubnetScoreRow.computed_at).label("max_ts"),
            )
            .group_by(SubnetScoreRow.netuid)
            .subquery()
        )

        rows = session.execute(
            select(SubnetScoreRow)
            .join(
                latest_sub,
                (SubnetScoreRow.netuid == latest_sub.c.netuid)
                & (SubnetScoreRow.computed_at == latest_sub.c.max_ts),
            )
            .order_by(desc(SubnetScoreRow.score))
        ).scalars().all()

    return [_row_to_dict(r) for r in rows]

def get_score_history(netuid: int, days: int = 30) -> list[dict]:
    """Return all score rows for a subnet over the past `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with SessionLocal() as session:
        rows = session.execute(
            select(SubnetScoreRow)
            .where(SubnetScoreRow.netuid == netuid)
            .where(SubnetScoreRow.computed_at >= since)
            .order_by(SubnetScoreRow.computed_at)
        ).scalars().all()
    return [_row_to_dict(r) for r in rows]


def get_score_at(netuid: int, timestamp: datetime) -> Optional[dict]:
    """Return the score row closest to (but not after) `timestamp`."""
    with SessionLocal() as session:
        row = session.execute(
            select(SubnetScoreRow)
            .where(SubnetScoreRow.netuid == netuid)
            .where(SubnetScoreRow.computed_at <= timestamp)
            .order_by(desc(SubnetScoreRow.computed_at))
            .limit(1)
        ).scalar_one_or_none()
    return _row_to_dict(row) if row else None


def get_top_subnets(n: int = 10) -> list[dict]:
    """Return top N subnets by latest score."""
    return get_latest_scores()[:n]


def get_scores_since(days: int = 90) -> list[dict]:
    """Return all score rows across subnets over the past `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with SessionLocal() as session:
        rows = session.execute(
            select(SubnetScoreRow)
            .where(SubnetScoreRow.computed_at >= since)
            .order_by(SubnetScoreRow.netuid, SubnetScoreRow.computed_at)
        ).scalars().all()
    return [_row_to_dict(r) for r in rows]


def get_score_distribution(buckets: int = 10) -> list[dict]:
    """
    Return a histogram of the latest score distribution.
    Each bucket covers a range of 100/buckets points.
    """
    latest = get_latest_scores()
    if not latest:
        return []

    bucket_size = 100.0 / buckets
    histogram = [
        {"range_start": i * bucket_size, "range_end": (i + 1) * bucket_size, "count": 0}
        for i in range(buckets)
    ]

    for row in latest:
        score = row["score"]
        idx = min(int(score / bucket_size), buckets - 1)
        histogram[idx]["count"] += 1

    return histogram


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _row_to_dict(row: SubnetScoreRow) -> dict:
    return {
        "id": row.id,
        "netuid": row.netuid,
        "score": row.score,
        "capital_score": row.capital_score,
        "activity_score": row.activity_score,
        "efficiency_score": row.efficiency_score,
        "health_score": row.health_score,
        "dev_score": row.dev_score,
        "rank": row.rank,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        "score_version": row.score_version,
        "alpha_price_tao": row.alpha_price_tao,
        "tao_in_pool": row.tao_in_pool,
        "market_cap_tao": row.market_cap_tao,
        "staking_apy": row.staking_apy,
        "raw_data": row.raw_data,
    }


def get_external_data_snapshot_map() -> dict[int, dict]:
    """Return the latest external evidence snapshot keyed by netuid."""
    with SessionLocal() as session:
        rows = session.execute(select(ExternalDataSnapshotRow)).scalars().all()
    return {
        row.netuid: {
            "github_url": row.github_url,
            "owner": row.owner,
            "repo": row.repo,
            "source_status": row.source_status,
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            "commits_30d": row.commits_30d,
            "contributors_30d": row.contributors_30d,
            "commits_90d": getattr(row, "commits_90d", 0),
            "contributors_90d": getattr(row, "contributors_90d", 0),
            "commits_180d": getattr(row, "commits_180d", 0),
            "contributors_180d": getattr(row, "contributors_180d", 0),
            "stars": row.stars,
            "forks": row.forks,
            "open_issues": row.open_issues,
            "last_push": row.last_push,
            "last_commit_at": getattr(row, "last_commit_at", None),
        }
        for row in rows
    }


def _sanitize_metadata_name(name: Optional[str], netuid: int) -> Optional[str]:
    if name is None:
        return None
    value = str(name).strip()
    if not value:
        return None
    if len(value) > 128:
        logger.warning("Skipping suspiciously long subnet name for SN%d (%d chars)", netuid, len(value))
        return None
    if any(token in value for token in ("taostats", "<", ">", "{", "}", "[", "]", '\\"', "\\u", "\\n")):
        logger.warning("Skipping suspicious subnet name payload for SN%d: %r", netuid, value[:80])
        return None
    return value[:128]
