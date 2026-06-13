from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import challenge as engine
from app.db import get_db
from app.models import Solve, Team
from app.schemas import (
    ChallengeSummary,
    HintResponse,
    PlayRequest,
    PlayResponse,
    SubmitFlagRequest,
    SubmitFlagResponse,
)
from app.security import get_current_team

router = APIRouter(prefix="/challenges", tags=["challenges"])


async def _solved_ids(db: AsyncSession, team_id) -> set[int]:
    rows = await db.scalars(select(Solve.challenge_id).where(Solve.team_id == team_id))
    return set(rows.all())


def _get_cfg(challenge_id: int):
    try:
        return engine.registry.get(challenge_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")


def _ensure_unlocked(cfg, solved: set[int]) -> None:
    if any(dep not in solved for dep in cfg.depends_on):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Challenge locked: solve its prerequisites first")


@router.get("", response_model=list[ChallengeSummary])
async def list_challenges(team: Team = Depends(get_current_team), db: AsyncSession = Depends(get_db)):
    solved = await _solved_ids(db, team.id)
    return [
        ChallengeSummary(
            id=cfg.id,
            name=cfg.name,
            slug=cfg.slug,
            owasp_tag=cfg.owasp_tag,
            base_points=cfg.base_points,
            depends_on=cfg.depends_on,
            locked=any(dep not in solved for dep in cfg.depends_on),
            solved=cfg.id in solved,
            hint_tiers=[{"tier": h.tier, "cost": h.cost} for h in cfg.hints],
        )
        for cfg in engine.registry.all()
    ]


@router.post("/{challenge_id}/play", response_model=PlayResponse)
async def play_challenge(
    challenge_id: int,
    body: PlayRequest,
    team: Team = Depends(get_current_team),
    db: AsyncSession = Depends(get_db),
):
    cfg = _get_cfg(challenge_id)
    _ensure_unlocked(cfg, await _solved_ids(db, team.id))
    result = await engine.play(db, team, challenge_id, body.prompt, body.fields)
    return PlayResponse(**result)


@router.post("/{challenge_id}/flag", response_model=SubmitFlagResponse)
async def submit_flag(
    challenge_id: int,
    body: SubmitFlagRequest,
    team: Team = Depends(get_current_team),
    db: AsyncSession = Depends(get_db),
):
    cfg = _get_cfg(challenge_id)
    _ensure_unlocked(cfg, await _solved_ids(db, team.id))
    result = await engine.submit_flag(db, team, challenge_id, body.flag)
    return SubmitFlagResponse(
        correct=result["correct"],
        already_solved=result.get("already_solved", False),
        first_blood=result.get("first_blood", False),
        points_awarded=result.get("points_awarded"),
        current_level=team.current_level,
        total_score=team.total_score,
    )


@router.post("/{challenge_id}/hints/{tier}", response_model=HintResponse)
async def request_hint(
    challenge_id: int,
    tier: int,
    team: Team = Depends(get_current_team),
    db: AsyncSession = Depends(get_db),
):
    cfg = _get_cfg(challenge_id)
    _ensure_unlocked(cfg, await _solved_ids(db, team.id))
    try:
        result = await engine.take_hint(db, team, challenge_id, tier)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such hint tier")
    return HintResponse(
        tier=result["tier"],
        text=result["text"],
        cost=result["cost"],
        charged=result["charged"],
        total_score=team.total_score,
    )
