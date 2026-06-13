"""Auth primitives.

Teams authenticate with an opaque random session token sent as ``Authorization: Bearer <token>``.
Only the SHA-256 hash is stored (treat the token like a password). Admins authenticate once with
``ADMIN_PASSWORD`` and receive a short-lived JWT.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import Session as TeamSession
from app.models import Team

settings = get_settings()
bearer = HTTPBearer(auto_error=True)
ADMIN_AUDIENCE = "ctf-admin"


# ── Token handling ───────────────────────────────────────────────────────────
def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_session_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token is shown to the client exactly once."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes)


# ── Admin auth ────────────────────────────────────────────────────────────────
def verify_admin_password(candidate: str) -> bool:
    return hmac.compare_digest(candidate.encode(), settings.admin_password.encode())


def create_admin_jwt() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin",
        "role": "admin",
        "aud": ADMIN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_admin_jwt(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=ADMIN_AUDIENCE)


# ── FastAPI dependencies ──────────────────────────────────────────────────────
async def get_current_team(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Team:
    now = datetime.now(timezone.utc)
    sess = await db.scalar(
        select(TeamSession).where(
            TeamSession.session_token_hash == hash_token(creds.credentials),
            TeamSession.revoked.is_(False),
            TeamSession.expires_at > now,
        )
    )
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired team session")
    team = await db.get(Team, sess.team_id)
    if team is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Team not found")
    team.last_seen_at = now
    await db.commit()
    return team


async def get_current_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return decode_admin_jwt(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin token")
