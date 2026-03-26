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
    score_version = Column(String(16), nullable=False, default="v1")
    raw_data = Column(JSON, nullable=True)

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


def create_tables() -> None:
    """Create all tables (idempotent, does not drop existing data)."""
    Base.metadata.create_all(bind=engine)


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
            raw_data=raw_data_by_netuid.get(s.netuid),
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
    with SessionLocal() as session:
        row = session.get(SubnetMetadataRow, netuid)
        if row is None:
            row = SubnetMetadataRow(netuid=netuid, first_seen=now)
            session.add(row)
        row.name = name
        row.github_url = github_url
        row.website = website
        row.last_updated = now
        session.commit()


# ---------------------------------------------------------------------------
# Read functions
# ---------------------------------------------------------------------------

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
    }
