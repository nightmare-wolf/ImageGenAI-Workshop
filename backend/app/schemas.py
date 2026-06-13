"""Pydantic request/response DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────
class TeamRegisterRequest(BaseModel):
    team_name: str = Field(min_length=2, max_length=64)
    access_code: str | None = None


class TeamRegisterResponse(BaseModel):
    team_id: uuid.UUID
    team_name: str
    session_token: str          # shown exactly once; client stores in localStorage
    current_level: int


class AdminLoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Challenges ────────────────────────────────────────────────────────────────
class ChallengeSummary(BaseModel):
    id: int
    name: str
    slug: str
    owasp_tag: str
    base_points: int
    depends_on: list[int]
    locked: bool
    solved: bool
    hint_tiers: list[dict]


class PlayRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    fields: dict[str, str] | None = None


class PlayResponse(BaseModel):
    assistant_message: str
    meta: dict


class SubmitFlagRequest(BaseModel):
    flag: str = Field(min_length=1, max_length=256)


class SubmitFlagResponse(BaseModel):
    correct: bool
    already_solved: bool = False
    first_blood: bool = False
    points_awarded: int | None = None
    current_level: int
    total_score: int


class HintResponse(BaseModel):
    tier: int
    text: str
    cost: int
    charged: bool
    total_score: int


# ── Leaderboard ───────────────────────────────────────────────────────────────
class LeaderboardEntry(BaseModel):
    rank: int
    team_name: str
    total_score: int
    solved_count: int
    current_level: int
    last_seen_at: datetime


class LeaderboardResponse(BaseModel):
    teams: list[LeaderboardEntry]


# ── Admin dashboard ───────────────────────────────────────────────────────────
class PerLevelProgress(BaseModel):
    challenge_id: int
    solved: bool
    is_first_blood: bool
    attempts: int
    flag_attempts: int
    hints_used: int


class AdminTeamProgress(BaseModel):
    team_id: uuid.UUID
    team_name: str
    total_score: int
    solved_count: int
    current_level: int
    hints_used: int
    attempts: int
    last_seen_at: datetime
    stuck: bool
    per_level: list[PerLevelProgress]


class ChallengeFirstBlood(BaseModel):
    id: int
    name: str
    first_blood_team: str | None
    first_blood_at: datetime | None
    solve_count: int


class AdminDashboardResponse(BaseModel):
    teams: list[AdminTeamProgress]
    challenges: list[ChallengeFirstBlood]
