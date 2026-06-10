"""FastAPI app factory. Mounts routers, middleware, and lifespan resources.

This is the Sprint-1 skeleton from docs/07-execution-roadmap.md Step 1. Routers referenced here are
implemented across Sprints 1–4; import-guarded so the skeleton runs as engines land.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # startup: open Redis pool, warm challenge configs, etc.
    app.state.settings = settings
    yield
    # shutdown: close pools


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ImageGenAI-Workshop CTF", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.env == "dev" else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers (mounted as they are implemented across sprints)
    from app.api import auth, challenges, generate, submit, hints, scoreboard, admin
    for router in (auth, challenges, generate, submit, hints, scoreboard, admin):
        app.include_router(router.router, prefix="/api")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "imagegen_mode": settings.imagegen_mode}

    return app


app = create_app()
