"""The challenge engine — the center of the architecture.

Everything else (auth, UI, leaderboard, RunPod) exists to support this. The engine:

  * loads config-driven challenges from ``challenges/level-NN.yaml`` (behavior lives in config, not code),
  * orchestrates a play turn   : render (system, user) -> LLM -> log Attempt -> return response,
  * validates flags            : idempotent Solve + first-blood + append-only ScoreEvent + unlock,
  * serves hints               : charge once via HintUsage + negative ScoreEvent.

Scoring is append-only: every points change is a ``ScoreEvent`` row; ``Team.total_score`` /
``hints_used`` are caches updated in the same transaction. The leaderboard is ``SUM(score_events)``.
"""
from __future__ import annotations

import glob
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import yaml
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.config import get_settings
from app.models import Attempt, Challenge, HintUsage, ScoreEvent, Solve, Team

settings = get_settings()
FIRST_BLOOD_BONUS = 50


# ── Config model ──────────────────────────────────────────────────────────────
@dataclass
class HintDef:
    tier: int
    cost: int
    text: str


@dataclass
class ChallengeConfig:
    id: int
    slug: str
    name: str
    owasp_tag: str
    base_points: int
    sort_order: int
    depends_on: list[int]
    system_prompt: str
    flag_value: str
    hints: list[HintDef] = field(default_factory=list)
    template_body: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "ChallengeConfig":
        flag = d.get("flag", {}) or {}
        hints = [HintDef(int(h["tier"]), int(h.get("cost", 0)), str(h.get("text", ""))) for h in d.get("hints", [])]
        return cls(
            id=int(d["id"]),
            slug=str(d["slug"]),
            name=str(d["name"]),
            owasp_tag=str(d.get("owasp_tag", "")),
            base_points=int(d.get("base_points", 0)),
            sort_order=int(d.get("sort_order", d.get("id", 0))),
            depends_on=[int(x) for x in d.get("depends_on", []) or []],
            system_prompt=str(d.get("system_prompt", "")).rstrip(),
            flag_value=str(flag.get("value") or flag.get("canonical") or "").strip(),
            hints=sorted(hints, key=lambda h: h.tier),
            template_body=(d.get("template") or {}).get("body"),
        )

    def public(self) -> dict:
        """Player-safe view — never exposes the flag or hint text."""
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "owasp_tag": self.owasp_tag,
            "base_points": self.base_points,
            "depends_on": self.depends_on,
            "hint_tiers": [{"tier": h.tier, "cost": h.cost} for h in self.hints],
        }


# ── Registry ──────────────────────────────────────────────────────────────────
class ChallengeRegistry:
    def __init__(self, directory: str):
        self.directory = directory
        self._by_id: dict[int, ChallengeConfig] = {}

    def load(self) -> None:
        by_id: dict[int, ChallengeConfig] = {}
        for path in sorted(glob.glob(os.path.join(self.directory, "level-*.yaml"))):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            cfg = ChallengeConfig.from_dict(data)
            by_id[cfg.id] = cfg
        self._by_id = by_id

    def get(self, challenge_id: int) -> ChallengeConfig:
        if challenge_id not in self._by_id:
            raise KeyError(challenge_id)
        return self._by_id[challenge_id]

    def all(self) -> list[ChallengeConfig]:
        return [self._by_id[k] for k in sorted(self._by_id)]


registry = ChallengeRegistry(settings.challenges_dir)


# ── Prompt rendering ────────────────────────────────────────────────────────--
def render_prompt(cfg: ChallengeConfig, prompt: str, fields: dict) -> tuple[str, str]:
    """Build the (system, user) pair sent to the model.

    MVP/Level 1 uses the naive split: the configured system prompt as the system turn, the player's
    text as the user turn. Later levels extend this with template bodies and unfiltered side-fields.
    """
    return cfg.system_prompt, (prompt or "")


# ── Scoring helper (append-only ledger + cache update) ──────────────────────────
def _record_score(db: AsyncSession, team: Team, challenge_id: int | None, points: int, reason: str) -> None:
    db.add(ScoreEvent(team_id=team.id, challenge_id=challenge_id, points=points, reason=reason))
    team.total_score = (team.total_score or 0) + points


# ── Engine operations ───────────────────────────────────────────────────────--
async def play(db: AsyncSession, team: Team, challenge_id: int, prompt: str, fields: dict | None = None) -> dict:
    cfg = registry.get(challenge_id)
    system, user = render_prompt(cfg, prompt, fields or {})
    result = await llm.generate(system, user)
    db.add(
        Attempt(
            team_id=team.id,
            challenge_id=challenge_id,
            kind="prompt",
            prompt=prompt,
            response_meta={"model": result.model, "latency_ms": result.latency_ms, "usage": result.usage},
        )
    )
    team.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return {"assistant_message": result.text, "meta": {"model": result.model, "latency_ms": result.latency_ms}}


async def submit_flag(db: AsyncSession, team: Team, challenge_id: int, flag: str) -> dict:
    cfg = registry.get(challenge_id)
    submitted = (flag or "").strip()
    correct = bool(cfg.flag_value) and hmac.compare_digest(submitted.lower(), cfg.flag_value.lower())

    db.add(
        Attempt(
            team_id=team.id,
            challenge_id=challenge_id,
            kind="flag",
            flag_submitted=submitted[:256],
            correct=correct,
        )
    )
    if not correct:
        await db.commit()
        return {"correct": False}

    existing = await db.scalar(
        select(Solve).where(Solve.team_id == team.id, Solve.challenge_id == challenge_id)
    )
    if existing is not None:
        await db.commit()
        return {"correct": True, "already_solved": True, "points_awarded": existing.points_awarded}

    # Lock the challenge row so concurrent solvers can't both claim first blood.
    chal = await db.scalar(select(Challenge).where(Challenge.id == challenge_id).with_for_update())
    is_first = chal is not None and chal.first_blood_team_id is None
    now = datetime.now(timezone.utc)
    awarded = cfg.base_points + (FIRST_BLOOD_BONUS if is_first else 0)

    db.add(
        Solve(
            team_id=team.id,
            challenge_id=challenge_id,
            points_awarded=awarded,
            is_first_blood=is_first,
            solved_at=now,
        )
    )
    _record_score(db, team, challenge_id, cfg.base_points, "solve")
    if is_first:
        chal.first_blood_team_id = team.id
        chal.first_blood_at = now
        _record_score(db, team, challenge_id, FIRST_BLOOD_BONUS, "first_blood")

    team.current_level = max(team.current_level, challenge_id + 1)
    team.last_seen_at = now

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # lost the unique-constraint race; another worker recorded the solve
        prior = await db.scalar(
            select(Solve).where(Solve.team_id == team.id, Solve.challenge_id == challenge_id)
        )
        return {"correct": True, "already_solved": True, "points_awarded": prior.points_awarded if prior else awarded}

    return {"correct": True, "already_solved": False, "first_blood": is_first, "points_awarded": awarded}


async def take_hint(db: AsyncSession, team: Team, challenge_id: int, tier: int) -> dict:
    cfg = registry.get(challenge_id)
    hint = next((h for h in cfg.hints if h.tier == tier), None)
    if hint is None:
        raise KeyError(f"no hint tier {tier} for challenge {challenge_id}")

    already = await db.scalar(
        select(HintUsage).where(
            HintUsage.team_id == team.id,
            HintUsage.challenge_id == challenge_id,
            HintUsage.tier == tier,
        )
    )
    if already is not None:
        return {"tier": tier, "text": hint.text, "cost": hint.cost, "charged": False}

    db.add(HintUsage(team_id=team.id, challenge_id=challenge_id, tier=tier, cost=hint.cost))
    if hint.cost:
        _record_score(db, team, challenge_id, -hint.cost, "hint")
    team.hints_used = (team.hints_used or 0) + 1

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # hint taken concurrently; don't double-charge
        return {"tier": tier, "text": hint.text, "cost": hint.cost, "charged": False}

    return {"tier": tier, "text": hint.text, "cost": hint.cost, "charged": True}
