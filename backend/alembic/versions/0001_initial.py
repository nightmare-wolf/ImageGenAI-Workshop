"""initial schema: teams, sessions, challenges, attempts, solves, hint_usages, score_events

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_name", sa.String(length=64), nullable=False),
        sa.Column("access_code_used", sa.String(length=128), nullable=True),
        sa.Column("current_level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("total_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("hints_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_team_name", "teams", ["team_name"], unique=True)

    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("owasp_tag", sa.String(length=16), nullable=False),
        sa.Column("base_points", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("depends_on", postgresql.ARRAY(sa.Integer()), server_default="{}", nullable=False),
        sa.Column("first_blood_team_id", sa.Uuid(), nullable=True),
        sa.Column("first_blood_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["first_blood_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_challenges_slug", "challenges", ["slug"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_team_id", "sessions", ["team_id"])
    op.create_index("ix_sessions_session_token_hash", "sessions", ["session_token_hash"], unique=True)

    op.create_table(
        "attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("flag_submitted", sa.String(length=256), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempts_team_challenge_created", "attempts", ["team_id", "challenge_id", "created_at"])
    op.create_index("ix_attempts_challenge_kind", "attempts", ["challenge_id", "kind"])

    op.create_table(
        "solves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_first_blood", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "challenge_id", name="uq_solve_team_challenge"),
    )
    op.create_index("ix_solves_challenge", "solves", ["challenge_id"])

    op.create_table(
        "hint_usages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "challenge_id", "tier", name="uq_hint_team_challenge_tier"),
    )

    op.create_table(
        "score_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_score_events_team", "score_events", ["team_id"])
    op.create_index("ix_score_events_created", "score_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("score_events")
    op.drop_table("hint_usages")
    op.drop_table("solves")
    op.drop_table("attempts")
    op.drop_index("ix_sessions_session_token_hash", table_name="sessions")
    op.drop_index("ix_sessions_team_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_challenges_slug", table_name="challenges")
    op.drop_table("challenges")
    op.drop_index("ix_teams_team_name", table_name="teams")
    op.drop_table("teams")
