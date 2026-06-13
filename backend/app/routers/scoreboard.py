from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ScoreEvent, Solve, Team
from app.schemas import LeaderboardEntry, LeaderboardResponse

router = APIRouter(tags=["scoreboard"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """Public, read-only. Source of truth is the append-only ledger: score = SUM(score_events)."""
    score_sq = (
        select(ScoreEvent.team_id, func.coalesce(func.sum(ScoreEvent.points), 0).label("score"))
        .group_by(ScoreEvent.team_id)
        .subquery()
    )
    solve_sq = (
        select(Solve.team_id, func.count().label("solved"))
        .group_by(Solve.team_id)
        .subquery()
    )
    q = (
        select(
            Team,
            func.coalesce(score_sq.c.score, 0),
            func.coalesce(solve_sq.c.solved, 0),
        )
        .outerjoin(score_sq, score_sq.c.team_id == Team.id)
        .outerjoin(solve_sq, solve_sq.c.team_id == Team.id)
        .order_by(
            func.coalesce(score_sq.c.score, 0).desc(),
            func.coalesce(solve_sq.c.solved, 0).desc(),
            Team.team_name.asc(),
        )
    )
    rows = (await db.execute(q)).all()
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            team_name=team.team_name,
            total_score=int(score),
            solved_count=int(solved),
            current_level=team.current_level,
            last_seen_at=team.last_seen_at,
        )
        for i, (team, score, solved) in enumerate(rows)
    ]
    return LeaderboardResponse(teams=entries)
