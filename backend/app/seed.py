"""Idempotent seeding of the Challenge registry into the DB.

Called from the FastAPI lifespan on startup (once per worker) and runnable standalone via
``python -m app.seed``. Uses a Postgres upsert so concurrent worker startups can't collide.
Only registry/metadata columns are synced — live state (first blood) is never touched.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.challenge import registry
from app.db import AsyncSessionLocal
from app.models import Challenge


async def seed_challenges() -> int:
    """Sync all challenge configs into the DB. Returns the number of challenges synced."""
    registry.load()
    cfgs = registry.all()
    if not cfgs:
        return 0

    values = [
        {
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "owasp_tag": c.owasp_tag,
            "base_points": c.base_points,
            "sort_order": c.sort_order,
            "depends_on": c.depends_on,
        }
        for c in cfgs
    ]
    stmt = pg_insert(Challenge).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Challenge.id],
        set_={
            "slug": stmt.excluded.slug,
            "name": stmt.excluded.name,
            "owasp_tag": stmt.excluded.owasp_tag,
            "base_points": stmt.excluded.base_points,
            "sort_order": stmt.excluded.sort_order,
            "depends_on": stmt.excluded.depends_on,
        },
    )
    async with AsyncSessionLocal() as db:
        await db.execute(stmt)
        await db.commit()
    return len(values)


if __name__ == "__main__":
    n = asyncio.run(seed_challenges())
    print(f"challenges seeded/updated: {n}")
