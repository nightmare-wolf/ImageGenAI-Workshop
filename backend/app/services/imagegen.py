"""Image generation client. One interface, two backends behind IMAGEGEN_MODE: `runpod` | `mock`.

The mock backend returns a watermarked placeholder plus synthetic provenance, so every challenge
except raw image aesthetics is fully developable offline and so the workshop can fail over from
RunPod to mock with a single env flip (see instructor failure-recovery playbook).
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import get_settings


@dataclass
class GenRequest:
    prompt: str
    negative_prompt: str = ""
    steps: int = 4
    seed: int = 0


@dataclass
class GenResult:
    image_b64: str
    # Raw provenance from the backend. The orchestrator/metadata writer decides how much of this to
    # embed in the served image per the challenge's `metadata.verbosity`.
    provenance: dict = field(default_factory=dict)
    blocked_by_safety: bool = False


class ImageGen(Protocol):
    async def generate(self, req: GenRequest) -> GenResult: ...


class MockImageGen:
    """CPU-only placeholder. Produces a deterministic 1x1-ish PNG and synthetic provenance."""
    async def generate(self, req: GenRequest) -> GenResult:
        png = _watermarked_placeholder(req.prompt, req.seed)
        return GenResult(
            image_b64=base64.b64encode(png).decode(),
            provenance={
                "model": "mock-sdxl-turbo",
                "steps": req.steps,
                "seed": req.seed,
                "worker_node_id": "mock-worker-0",
            },
        )


class RunPodImageGen:
    """Calls a RunPod serverless endpoint. Timeout + retry; safety classifier runs in the handler."""
    def __init__(self):
        s = get_settings()
        import runpod  # lazy import so mock-only dev needs no SDK
        runpod.api_key = s.runpod_api_key
        self._endpoint = runpod.Endpoint(s.runpod_endpoint_id)
        self._timeout = s.imagegen_timeout_seconds

    async def generate(self, req: GenRequest) -> GenResult:
        out = self._endpoint.run_sync(
            {"input": {"prompt": req.prompt, "negative_prompt": req.negative_prompt,
                       "steps": req.steps, "seed": req.seed}},
            timeout=self._timeout,
        )
        if out.get("error") == "blocked_by_safety":
            return GenResult(image_b64=out["image"], blocked_by_safety=True)
        return GenResult(image_b64=out["image_b64"], provenance=out.get("provenance", {}))


def get_imagegen() -> ImageGen:
    return RunPodImageGen() if get_settings().imagegen_mode == "runpod" else MockImageGen()


def _watermarked_placeholder(prompt: str, seed: int) -> bytes:
    """Tiny PNG with a visible 'MOCK' watermark; replace with Pillow rendering in implementation."""
    # Minimal valid 1x1 PNG; the real mock uses Pillow to draw the prompt + 'MOCK' watermark.
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
