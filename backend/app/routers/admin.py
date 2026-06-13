import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import challenge as engine
from app.db import get_db
from app.models import Attempt, Challenge, HintUsage, ScoreEvent, Solve, Team
from app.schemas import (
    AdminDashboardResponse,
    AdminLoginRequest,
    AdminTeamProgress,
    ChallengeFirstBlood,
    PerLevelProgress,
    TokenResponse,
)
from app.security import create_admin_jwt, get_current_admin, verify_admin_password

router = APIRouter(prefix="/admin", tags=["admin"])

ACTIVE_WINDOW_S = 1200   # seen in last 20 min => "active"
STALL_WINDOW_S = 900     # no solve in last 15 min => not progressing


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest):
    if not verify_admin_password(body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin password")
    return TokenResponse(access_token=create_admin_jwt())


async def _build_dashboard(db: AsyncSession) -> AdminDashboardResponse:
    now = datetime.now(timezone.utc)
    teams = (await db.scalars(select(Team))).all()
    team_name = {t.id: t.team_name for t in teams}

    score_by = {
        tid: int(s)
        for tid, s in (
            await db.execute(
                select(ScoreEvent.team_id, func.coalesce(func.sum(ScoreEvent.points), 0)).group_by(ScoreEvent.team_id)
            )
        ).all()
    }

    solved_by: dict = {}      # team_id -> {challenge_id: is_first_blood}
    for tid, cid, fb in (await db.execute(select(Solve.team_id, Solve.challenge_id, Solve.is_first_blood))).all():
        solved_by.setdefault(tid, {})[cid] = fb

    last_solve = {
        tid: ts
        for tid, ts in (await db.execute(select(Solve.team_id, func.max(Solve.solved_at)).group_by(Solve.team_id))).all()
    }

    attempts_by: dict = {}    # (team_id, challenge_id) -> {kind: count}
    for tid, cid, kind, n in (
        await db.execute(
            select(Attempt.team_id, Attempt.challenge_id, Attempt.kind, func.count()).group_by(
                Attempt.team_id, Attempt.challenge_id, Attempt.kind
            )
        )
    ).all():
        attempts_by.setdefault((tid, cid), {})[kind] = int(n)

    hints_by = {
        (tid, cid): int(n)
        for tid, cid, n in (
            await db.execute(
                select(HintUsage.team_id, HintUsage.challenge_id, func.count()).group_by(
                    HintUsage.team_id, HintUsage.challenge_id
                )
            )
        ).all()
    }

    cfgs = engine.registry.all()
    team_progress: list[AdminTeamProgress] = []
    for t in teams:
        per_level = []
        total_attempts = 0
        for cfg in cfgs:
            a = attempts_by.get((t.id, cfg.id), {})
            prompts, flags = a.get("prompt", 0), a.get("flag", 0)
            total_attempts += prompts + flags
            per_level.append(
                PerLevelProgress(
                    challenge_id=cfg.id,
                    solved=cfg.id in solved_by.get(t.id, {}),
                    is_first_blood=bool(solved_by.get(t.id, {}).get(cfg.id, False)),
                    attempts=prompts + flags,
                    flag_attempts=flags,
                    hints_used=hints_by.get((t.id, cfg.id), 0),
                )
            )
        ls = last_solve.get(t.id)
        active = bool(t.last_seen_at) and (now - t.last_seen_at).total_seconds() < ACTIVE_WINDOW_S
        not_progressing = ls is None or (now - ls).total_seconds() > STALL_WINDOW_S
        team_progress.append(
            AdminTeamProgress(
                team_id=t.id,
                team_name=t.team_name,
                total_score=score_by.get(t.id, 0),
                solved_count=len(solved_by.get(t.id, {})),
                current_level=t.current_level,
                hints_used=t.hints_used,
                attempts=total_attempts,
                last_seen_at=t.last_seen_at,
                stuck=active and not_progressing,
                per_level=per_level,
            )
        )
    team_progress.sort(key=lambda x: x.total_score, reverse=True)

    solve_count = {
        cid: int(n)
        for cid, n in (await db.execute(select(Solve.challenge_id, func.count()).group_by(Solve.challenge_id))).all()
    }
    chal_rows = (await db.scalars(select(Challenge))).all()
    challenges = [
        ChallengeFirstBlood(
            id=c.id,
            name=c.name,
            first_blood_team=team_name.get(c.first_blood_team_id),
            first_blood_at=c.first_blood_at,
            solve_count=solve_count.get(c.id, 0),
        )
        for c in sorted(chal_rows, key=lambda c: c.sort_order)
    ]
    return AdminDashboardResponse(teams=team_progress, challenges=challenges)


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard(_: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return await _build_dashboard(db)


@router.get("/export.csv")
async def export_csv(_: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    d = await _build_dashboard(db)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["team_name", "total_score", "current_level", "challenge_id", "solved", "attempts", "flag_attempts", "hints_used"]
    )
    for t in d.teams:
        for p in t.per_level:
            w.writerow(
                [t.team_name, t.total_score, t.current_level, p.challenge_id, int(p.solved), p.attempts, p.flag_attempts, p.hints_used]
            )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ctf_progress.csv"},
    )
