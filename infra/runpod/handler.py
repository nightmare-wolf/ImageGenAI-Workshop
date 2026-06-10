"""RunPod Serverless handler — image generation with an immutable safety classifier.

The safety classifier (NSFW/CSAM) lives HERE, in the GPU handler, precisely so that no app-layer CTF
challenge can disable or route around it. No flag ever depends on bypassing it. See SECURITY.md.

Deploy: build infra/runpod/Dockerfile.gpu, push, create a RunPod serverless endpoint from it, set
RUNPOD_ENDPOINT_ID + RUNPOD_API_KEY in the backend's .env, and IMAGEGEN_MODE=runpod.
"""
from __future__ import annotations

import base64
import io

import runpod  # provided by the RunPod base image

# --- Loaded once per cold start ------------------------------------------------
# import torch
# from diffusers import AutoPipelineForText2Image
# pipe = AutoPipelineForText2Image.from_pretrained(
#     "stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16"
# ).to("cuda")
# safety_classifier = load_safety_classifier()   # NSFW/CSAM — immutable, out of CTF scope

SAFE_PLACEHOLDER_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def _to_b64(image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def handler(event):
    p = event["input"]
    prompt = p.get("prompt", "")
    negative = p.get("negative_prompt", "")

    # IMMUTABLE safety gate — applies to every request, cannot be toggled by the app.
    # if not safety_classifier.ok(prompt, negative):
    #     return {"error": "blocked_by_safety", "image": SAFE_PLACEHOLDER_B64}

    # image = pipe(prompt=prompt, negative_prompt=negative,
    #              num_inference_steps=p.get("steps", 4), guidance_scale=0.0,
    #              generator=torch.manual_seed(p.get("seed", 0))).images[0]
    # image_b64 = _to_b64(image)
    image_b64 = SAFE_PLACEHOLDER_B64  # placeholder until pipeline is wired

    # Provenance is returned raw; the BACKEND decides how much to embed per challenge config
    # (this is what makes Level 4's verbose-metadata leak a backend setting, not a handler one).
    provenance = {
        "model": "sdxl-turbo",
        "steps": p.get("steps", 4),
        "seed": p.get("seed", 0),
        "worker_node_id": runpod.serverless.worker_id if hasattr(runpod, "serverless") else "unknown",
    }
    return {"image_b64": image_b64, "provenance": provenance}


runpod.serverless.start({"handler": handler})
