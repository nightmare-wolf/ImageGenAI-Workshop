"""Scoring engine — idempotent first-solve scoring with rank decay + first-blood + writeup bonus.

Reference implementation for Phase 6 §8.

  score = base_points
        − Σ hint_costs_taken
        − decay(solve_rank)          # rank-based, NOT time-based (cold starts shouldn't penalize)
        + first_blood_bonus          # solve_rank == 1
        + writeup_bonus              # L8 only, judged 0..200

Postgres is the source of truth; the live scoreboard is a Redis sorted set mirrored on each solve.
First-blood is decided inside the solve transaction to avoid races.
"""
from __future__ import annotations

from dataclasses import dataclass

FIRST_BLOOD_BONUS = 50
DECAY_STEP = 5          # points shaved per solve rank
DECAY_FLOOR = 0.5       # never decay a challenge below 50% of base


@dataclass
class ScoreInputs:
    base_points: int
    hint_costs: list[int]
    solve_rank: int          # 1 = first solver of this challenge
    writeup_bonus: int = 0   # L8 only


def decay(base_points: int, solve_rank: int) -> int:
    """Small rank-based step-down; clamped so late solvers still earn a fair share."""
    penalty = DECAY_STEP * max(0, solve_rank - 1)
    floored = int(base_points * DECAY_FLOOR)
    return max(floored, base_points - penalty)


def compute_score(i: ScoreInputs) -> int:
    points = decay(i.base_points, i.solve_rank)
    points -= sum(i.hint_costs)
    if i.solve_rank == 1:
        points += FIRST_BLOOD_BONUS
    points += i.writeup_bonus
    return max(0, points)


# ── Persistence (pseudo-DAL; wire to SQLAlchemy + Redis in app.services) ─────
class ScoringService:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def record_solve(self, user_id: str, challenge_id: int, *, writeup_bonus: int = 0) -> int | None:
        """Idempotent: only the first correct submission per (user, challenge) scores.

        Returns awarded points, or None if already solved. The solve_rank is computed in the same
        transaction (SELECT ... FOR UPDATE on a per-challenge counter) so concurrent first-bloods
        can't both win rank 1.
        """
        async with self.db.begin() as tx:
            if await self._already_solved(tx, user_id, challenge_id):
                return None
            solve_rank = await self._next_solve_rank(tx, challenge_id)   # locked counter
            base = await self._base_points(tx, challenge_id)
            hint_costs = await self._hint_costs(tx, user_id, challenge_id)
            awarded = compute_score(ScoreInputs(base, hint_costs, solve_rank, writeup_bonus))
            await self._insert_solve(tx, user_id, challenge_id, solve_rank, awarded)
            await self._bump_total(tx, user_id, awarded)

        total = await self._total(user_id)
        await self.redis.zadd("scoreboard", {user_id: total})   # mirror for live board
        await self.redis.publish("scoreboard:update", user_id)  # nudge WS subscribers
        return awarded

    # --- the following are thin DB wrappers; omitted here for brevity ---
    async def _already_solved(self, tx, u, c): ...
    async def _next_solve_rank(self, tx, c): ...   # SELECT count(*)+1 FROM solves WHERE challenge_id=c FOR UPDATE
    async def _base_points(self, tx, c): ...
    async def _hint_costs(self, tx, u, c): ...
    async def _insert_solve(self, tx, u, c, rank, pts): ...
    async def _bump_total(self, tx, u, pts): ...
    async def _total(self, u): ...
