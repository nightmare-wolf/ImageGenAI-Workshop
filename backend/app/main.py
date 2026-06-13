"""FastAPI entrypoint. Lifespan loads the challenge registry and seeds the DB."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.challenge import registry
from app.config import get_settings
from app.routers import admin, auth, challenge, scoreboard
from app.seed import seed_challenges

settings = get_settings()
log = logging.getLogger("ctf")


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()
    try:
        n = await seed_challenges()
        log.info("seeded %s challenges", n)
    except Exception as exc:  # never block boot on a seed race; another worker will have done it
        log.warning("challenge seed skipped: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ImageGenAI-Workshop CTF API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=False,   # bearer tokens, not cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (auth.router, challenge.router, scoreboard.router, admin.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/healthz", tags=["meta"])
    async def healthz():
        return {
            "status": "ok",
            "llm_mode": settings.llm_mode,
            "challenges_loaded": len(registry.all()),
        }

    return app


app = create_app()
