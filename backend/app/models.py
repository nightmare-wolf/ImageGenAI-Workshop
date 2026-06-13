"""SQLAlchemy 2.x models.

Source of truth for scoring is the append-only ``ScoreEvent`` table (leaderboard = SUM(points)).
``Team.total_score`` / ``Team.hints_used`` are denormalized caches updated in the same transaction
that appends the event — never recomputed from solves.

The ``Challenge`` row is registry + live state only (points, ordering, first blood). The actual
vulnerable behavior is config-driven from ``challenges/level-NN.yaml``, loaded by the challenge
engine — the engine is the center of the architecture, not these tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    team_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    access_code_used: Mapped[str | None] = mapped_column(String(128), default=None)
    current_level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    total_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")   # cache of SUM(score_events)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")     # cache
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list[Session]] = relationship(back_populates="team", cascade="all, delete-orphan")
    attempts: Mapped[list[Attempt]] = relationship(back_populates="team", cascade="all, delete-orphan")
    solves: Mapped[list[Solve]] = relationship(back_populates="team", cascade="all, delete-orphan")
    hint_usages: Mapped[list[HintUsage]] = relationship(back_populates="team", cascade="all, delete-orphan")
    score_events: Mapped[list[ScoreEvent]] = relationship(back_populates="team", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 hex
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    team: Mapped[Team] = relationship(back_populates="sessions")


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)            # 0..8, matches YAML id
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    owasp_tag: Mapped[str] = mapped_column(String(16))
    base_points: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer)
    depends_on: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")

    # BSides flavor: first blood / fastest solve recognition.
    first_blood_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), default=None
    )
    first_blood_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    first_blood_team: Mapped[Team | None] = relationship(foreign_keys=[first_blood_team_id])


class Attempt(Base):
    """Every logged interaction with a challenge: prompt submissions and flag submissions."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16))                # 'prompt' | 'flag'
    prompt: Mapped[str | None] = mapped_column(Text, default=None)
    response_meta: Mapped[dict | None] = mapped_column(JSONB, default=None)  # model, latency_ms, tokens, etc.
    flag_submitted: Mapped[str | None] = mapped_column(String(256), default=None)
    correct: Mapped[bool | None] = mapped_column(Boolean, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team] = relationship(back_populates="attempts")
    challenge: Mapped[Challenge] = relationship()

    __table_args__ = (
        Index("ix_attempts_team_challenge_created", "team_id", "challenge_id", "created_at"),
        Index("ix_attempts_challenge_kind", "challenge_id", "kind"),
    )


class Solve(Base):
    __tablename__ = "solves"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"))
    solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_first_blood: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    points_awarded: Mapped[int] = mapped_column(Integer)

    team: Mapped[Team] = relationship(back_populates="solves")
    challenge: Mapped[Challenge] = relationship()

    __table_args__ = (
        UniqueConstraint("team_id", "challenge_id", name="uq_solve_team_challenge"),
        Index("ix_solves_challenge", "challenge_id"),
    )


class HintUsage(Base):
    __tablename__ = "hint_usages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"))
    tier: Mapped[int] = mapped_column(Integer)
    cost: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team] = relationship(back_populates="hint_usages")
    challenge: Mapped[Challenge] = relationship()

    __table_args__ = (
        UniqueConstraint("team_id", "challenge_id", "tier", name="uq_hint_team_challenge_tier"),
    )


class ScoreEvent(Base):
    """Append-only ledger. Leaderboard = SUM(points). Never updated or deleted."""

    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    challenge_id: Mapped[int | None] = mapped_column(
        ForeignKey("challenges.id", ondelete="SET NULL"), default=None
    )
    points: Mapped[int] = mapped_column(Integer)                  # may be negative (hints)
    reason: Mapped[str] = mapped_column(String(32))              # 'solve' | 'hint' | 'first_blood' | 'adjustment'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team] = relationship(back_populates="score_events")

    __table_args__ = (
        Index("ix_score_events_team", "team_id"),
        Index("ix_score_events_created", "created_at"),
    )
