# Phase 5 — Technical Stack

Each choice is optimized for three constraints that dominate this project: **browser-only for
participants**, **limited infra budget**, and **a 3-hour event where reliability beats elegance**.

| Layer | Choice | One-line why |
|-------|--------|--------------|
| Frontend | **React 18 + TypeScript + Vite + Tailwind** | Fast to build, ubiquitous, zero-install for attendees |
| Backend | **Python 3.12 + FastAPI** | Same language as the AI/image ecosystem; async; great DX |
| Database | **PostgreSQL 16** | One boring, reliable store for identity/attempts/scores/audit |
| Cache/state | **Redis 7** | Sessions, rate limits, turn-memory, live scoreboard |
| Containers | **Docker + Compose**, multi-stage builds | Reproducible dev → identical prod images |
| GPU/deploy | **RunPod Serverless** | Pay-per-second, scale-to-zero, autoscale to attendee load |
| Image gen | **ComfyUI or Diffusers (SDXL-Turbo / SD 1.5)** + safety classifier | Few-step = cheap/fast; workflow flexibility for challenges |
| Observability | **Grafana + Loki + Prometheus** | Instructor dashboard + audit + after-action, all OSS |
| Auth | **Access-code → JWT (self-issued)** | Zero-friction, no PII, offline-capable |

---

## Frontend framework — React + TypeScript + Vite + Tailwind

**Why.** The hard requirement is *participants need only a browser*. React is the most widely known
SPA framework (lowest contributor friction for an open-source workshop repo), TypeScript catches the
request/response-shape bugs that would otherwise eat playtest time, Vite gives instant dev rebuilds,
and Tailwind lets one engineer make a projector-legible scoreboard without a designer. TanStack Query
handles the polling/refetch of scoreboard and challenge state; Zustand holds trivial UI state.
**Why not** Next.js/SSR: we have no SEO/SSR need and a static SPA + JSON API is simpler to containerize
and reason about for a security tool. **Why not** htmx/server-rendered: we *want* a rich client so
DevTools-driven request editing is natural — that's pedagogically central.

## Backend framework — FastAPI (Python)

**Why.** The image/AI ecosystem (Diffusers, transformers, OCR, safety classifiers, RunPod SDK) is
Python-first, so the orchestration layer lives where the libraries live. FastAPI gives async I/O
(important when fanning out to RunPod), Pydantic v2 for strict request/response schemas (which
doubles as documentation and as the boundary where we *intentionally* relax validation per
challenge), and auto-generated OpenAPI docs that attendees can explore. **Why not** Node/Express:
would split the stack from the AI libraries. **Why not** Go: great for the proxy/scoreboard but the
orchestration glue would fight the ecosystem; not worth two languages for a workshop.

## Database — PostgreSQL

**Why.** We need durable, queryable records of identity, every attempt (audit), solves, and scores,
plus JSONB for per-session `rotating_state`. Postgres does relational + JSONB + strong consistency in
one boring, well-understood engine — exactly what you want for the *source of truth* of a scored
competition. **Why not** SQLite: fine for solo dev, but concurrent writes from 50 attendees + the
audit stream want a real server. **Why not** a NoSQL store: scoring and first-blood need transactional
guarantees.

## Cache / state — Redis

**Why.** Three jobs that Postgres shouldn't carry on the hot path: per-token/IP **rate limiting**,
**multi-turn session memory** (L6/L8, with TTL), and the **live scoreboard** (a sorted set the WS
endpoint reads so the projector updates without DB load). **Why not** in-process memory: we want it
to survive a backend restart mid-workshop and to be shared if we scale to >1 worker.

## Container strategy — Docker + Compose, multi-stage

**Why.** One `docker-compose.yml` brings up the entire stack for dev and for a single-VM workshop
deploy; multi-stage builds keep images small and dev/prod identical. The image-gen container has a
**mock** variant (CPU, watermarked placeholders) so the whole platform is developable without a GPU —
critical for contributors and for the RunPod-failover story. **Why not** Kubernetes: massive
operational overhead for a 3-hour, single-node event; Compose (or a managed container host) is right-
sized. The GPU workload deliberately lives *outside* Compose on RunPod.

## RunPod deployment strategy — Serverless GPU endpoint

**Why.** Image generation is the only GPU cost and it is **bursty** (50 people clicking "generate"
during CTF blocks, near-idle during debriefs). RunPod Serverless bills **per second** and
**scales to zero**, so we pay for actual generation, not idle GPUs — the right model for a limited
budget. Strategy:
- Package the image pipeline + safety classifier as a RunPod serverless **handler** (`infra/runpod/handler.py`).
- Use a mid-tier GPU (RTX 4090 / A4000-class) — SDXL-Turbo/SD-1.5 at low step counts renders in a
  few seconds, well within those tiers' memory.
- **Pre-warm active workers** before CTF blocks to kill cold-starts; **scale to zero** during
  debriefs/breaks. Set a **max-workers ceiling** and a **hard spend cap** as budget guardrails.
- Backend talks to the endpoint via the RunPod SDK behind `IMAGEGEN_MODE=runpod|mock`, so a bad
  GPU day is a one-flag failover. Full sizing/cost in [cost-estimate.md](cost-estimate.md).

**Why not** a dedicated GPU pod/VM: you pay 24/7 for a 3-hour burst. **Why not** a hosted image API:
less control over the *workflow internals* we need to deliberately make vulnerable (metadata,
templates, tools), and per-call pricing for a captive workshop is usually worse than per-second
serverless you control.

## Image generation framework — ComfyUI or Diffusers, SDXL-Turbo / SD 1.5

**Why.** Two viable options, both supported by the handler abstraction:
- **Diffusers (HF)** — simplest to script, easiest to embed our metadata/provenance and to expose the
  "workflow" internals the challenges attack. Recommended default for buildability.
- **ComfyUI** — graph/workflow engine; better if we want the "image generation *workflow*" to be a
  first-class, inspectable artifact (fits the metadata/template challenges thematically) and to let
  advanced attendees see node graphs.
**Model choice:** **SDXL-Turbo or SD 1.5** at low step counts — a few seconds per image on mid-tier
GPUs keeps both **latency** (50 people waiting) and **cost** (per-second billing) low. A mandatory,
immutable **safety classifier** (NSFW/CSAM) wraps every generation and is **out of CTF scope**.
**Why not** Flux/SDXL-full at high steps: slower and pricier with no pedagogical benefit — the flags
are in the app layer, not image fidelity.

## Observability stack — Grafana + Loki + Prometheus

**Why.** We need three things in one place: an **instructor live dashboard** (solve counts, stuck
heatmap, RunPod health/spend), a **security/audit** record (every prompt/response/flag verdict), and
**after-action** analytics for awards/writeups. The Grafana + Loki (logs) + Prometheus (metrics)
trio is the OSS standard, runs in Compose, and has a generous Grafana Cloud free tier if we'd rather
not self-host on event day. **Why not** a SaaS APM (Datadog/etc.): cost and overkill for a one-day
event; **why not** just printing logs: the instructor needs *live* room visibility to pace the
workshop.

## Authentication provider — self-issued access-code → JWT

**Why.** For a 3-hour conference workshop the goals are *zero friction, no PII, works on hostile
Wi-Fi, revocable*. Organizers pre-generate single-use **access codes**; redeeming one mints a
short-TTL **JWT** with `user/team/role` claims. No external IdP to depend on, no accounts to clean
up, no privacy footprint to manage. **Why not** OAuth/SSO (Auth0/Clerk/Google): external dependency
+ network egress + privacy overhead for an ephemeral event, and many attendees won't want to OAuth
into a deliberately-vulnerable app. **Why not** username/password: PII + reset flows + storage risk
for zero benefit. If this platform were ever run as a persistent public service, swapping in an OIDC
provider is a contained change behind the existing AuthN/Z module.

---

### Summary rationale

Every choice trades novelty for **reliability and low operating cost** because the failure mode that
actually ruins a workshop is *infrastructure flakiness during the live event*, not an unfashionable
framework. The one place we spend on flexibility is the **image-gen + RunPod serverless** path,
because that's where both the cost risk and the pedagogical surface (workflow internals, metadata,
tools) live.
