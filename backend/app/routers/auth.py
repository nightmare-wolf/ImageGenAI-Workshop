from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import Session as TeamSession
from app.models import Team
from app.schemas import TeamRegisterRequest, TeamRegisterResponse
from app.security import new_session_token, session_expiry

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TeamRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_team(body: TeamRegisterRequest, db: AsyncSession = Depends(get_db)):
    if settings.event_access_code and (body.access_code or "") != settings.event_access_code:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid event access code")

    name = body.team_name.strip()
    if await db.scalar(select(Team).where(Team.team_name == name)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Team name already taken")

    team = Team(team_name=name, access_code_used=(body.access_code or None))
    db.add(team)
    raw, token_hash = new_session_token()
    try:
        await db.flush()  # assign team.id
        db.add(TeamSession(team_id=team.id, session_token_hash=token_hash, expires_at=session_expiry()))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Team name already taken")

    await db.refresh(team)  # load server-side defaults (current_level, timestamps)
    return TeamRegisterResponse(
        team_id=team.id,
        team_name=team.team_name,
        session_token=raw,
        current_level=team.current_level,
    )
