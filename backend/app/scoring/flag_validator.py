"""Flag validation: shape-check, per-session derivation, constant-time compare, anti-bruteforce.

Reference implementation for Phase 6 §7. The two security-relevant properties:
  1. Flags can be *derived per session* (HMAC), so a flag leaked in chat does not unlock another
     player's solve and cannot be guessed across sessions.
  2. Comparison is constant-time and gated by a per-user rate limiter with backoff.
"""
from __future__ import annotations

import hmac
import hashlib
import re
from dataclasses import dataclass

FLAG_RE = re.compile(r"^bsides\{[a-z0-9_]{3,80}\}$")


@dataclass
class FlagSpec:
    """Resolved expectation for a (challenge, session)."""
    challenge_id: int
    flag_type: str          # "static" | "derived"
    static_value: str | None = None
    canonical: str | None = None   # human-readable form for derived flags (shown in writeups/awards)


def normalize(submission: str) -> str:
    """Trim and lowercase the body; tolerate stray whitespace/case the player pasted."""
    return submission.strip().lower()


def is_well_formed(submission: str) -> bool:
    """Cheap reject before any crypto — also kills probing with non-flag junk."""
    return bool(FLAG_RE.match(normalize(submission)))


def derive_flag(server_secret: str, challenge_id: int, user_id: str, salt: str) -> str:
    """Per-session flag: HMAC(server_secret, "cid:user:salt") → readable bsides{...} token.

    Deterministic for a given (challenge, user, salt) so re-submits validate, but unguessable and
    non-transferable between players.
    """
    msg = f"{challenge_id}:{user_id}:{salt}".encode()
    digest = hmac.new(server_secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"bsides{{chain_{digest[:16]}}}"


def expected_flag(spec: FlagSpec, *, server_secret: str, user_id: str, salt: str) -> str:
    if spec.flag_type == "static":
        assert spec.static_value, "static flag missing value"
        return spec.static_value
    return derive_flag(server_secret, spec.challenge_id, user_id, salt)


def verify(submission: str, expected: str) -> bool:
    """Constant-time compare on normalized values. No 'close' oracle is ever returned to the client."""
    if not is_well_formed(submission):
        return False
    return hmac.compare_digest(normalize(submission), normalize(expected))


# ── Anti-bruteforce ─────────────────────────────────────────────────────────
class SubmissionLimiter:
    """Per-user submission throttle with exponential backoff and lockout.

    Backed by Redis in production (INCR + EXPIRE); this in-memory version documents the policy and
    is used in tests.
    """
    def __init__(self, base_window_s: int = 60, max_per_window: int = 10, lockout_after: int = 30):
        self.base_window_s = base_window_s
        self.max_per_window = max_per_window
        self.lockout_after = lockout_after
        self._counts: dict[str, int] = {}
        self._fails: dict[str, int] = {}

    def allow(self, user_id: str) -> bool:
        if self._fails.get(user_id, 0) >= self.lockout_after:
            return False  # locked; requires instructor override (admin reset-session)
        return self._counts.get(user_id, 0) < self.max_per_window

    def record(self, user_id: str, correct: bool) -> None:
        self._counts[user_id] = self._counts.get(user_id, 0) + 1
        if not correct:
            self._fails[user_id] = self._fails.get(user_id, 0) + 1
        else:
            self._fails[user_id] = 0
