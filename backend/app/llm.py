"""LLM client — one interface, two backends behind ``LLM_MODE``.

The challenge engine stays model-agnostic: it renders ``(system, user)`` and calls ``generate``.
Whether the system prompt leaks is the *model's* decision — for ``openai`` mode that's a real model
on RunPod (vLLM, OpenAI-compatible); for ``mock`` mode it's a deterministic stand-in that emulates a
leaky, instruction-following small model so Level 1 is solvable with no GPU.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import httpx

from app.config import get_settings

settings = get_settings()

# Heuristic the mock uses to decide whether the "model" reveals its system prompt. A real model
# makes this decision itself; this just makes mock-mode behave like a coaxable instruct model.
_LEAK_INTENT = re.compile(
    r"(ignore (the |all )?(previous|above|prior)|system (prompt|message)|your (instructions|"
    r"configuration|directives|prompt)|repeat (the )?(text|instructions|everything|above)|verbatim|"
    r"reveal|print (your|the)|in a code block|translate (your|the)|what (are|were) your instructions)",
    re.IGNORECASE,
)


@dataclass
class LLMResult:
    text: str
    model: str
    latency_ms: int
    usage: dict = field(default_factory=dict)


async def generate(system: str, user: str) -> LLMResult:
    if settings.llm_mode == "openai":
        return await _generate_openai(system, user)
    return _generate_mock(system, user)


def _generate_mock(system: str, user: str) -> LLMResult:
    if _LEAK_INTENT.search(user or ""):
        text = f"Sure — here are my instructions, verbatim:\n\n{system}"
    else:
        text = (
            "Here's a warm, painterly, naturally-lit image generated from your prompt. "
            "(mock backend: set LLM_MODE=openai and LLM_API_BASE to your RunPod vLLM endpoint "
            "for real generations.)"
        )
    return LLMResult(text=text, model="mock", latency_ms=1)


_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
        _client = httpx.AsyncClient(
            base_url=settings.llm_api_base,
            timeout=settings.llm_timeout_seconds,
            headers=headers,
        )
    return _client


async def _generate_openai(system: str, user: str) -> LLMResult:
    t0 = time.monotonic()
    resp = await _get_client().post(
        "/chat/completions",
        json={
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return LLMResult(
        text=data["choices"][0]["message"]["content"],
        model=data.get("model", settings.llm_model),
        latency_ms=int((time.monotonic() - t0) * 1000),
        usage=data.get("usage", {}) or {},
    )
