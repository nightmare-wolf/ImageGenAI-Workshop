# Phase 7 — Execution Roadmap

An actionable, file-by-file roadmap to start coding immediately. Each step lists exact files,
purpose, recommended structure, key technical decisions, and pitfalls. Steps 1–2 are scaffolded in
this repo already; follow the same pattern for 3–5.

---

## Step 1 — Initialize repository structure

**Files to create**
| File | Purpose |
|------|---------|
| `.gitignore`, `.env.example` | Hygiene + documented config surface |
| `infra/docker-compose.yml` | Whole stack: postgres, redis, backend, frontend, caddy, observability |
| `backend/pyproject.toml`, `backend/Dockerfile` | Backend deps + multi-stage image |
| `backend/app/main.py` | FastAPI app factory: routers, middleware, lifespan |
| `backend/app/core/config.py` | Pydantic `Settings` from env (`IMAGEGEN_MODE`, secrets, DB/Redis URLs) |
| `backend/alembic/…` | Baseline migration (the schema in [06](06-build-artifacts.md#2-database-schema)) |
| `frontend/` Vite scaffold | SPA shell + API client |

**Recommended structure.** App factory pattern (`create_app()`), settings via env, routers mounted
under `/api`. Compose default `IMAGEGEN_MODE=mock` so `up` works with no GPU/secret.

**Technical decisions.** Mock-first image gen; `.env.example` documents every var; one compose file
for dev, an override for prod. Single backend container holds all engines (no premature
microservices).

**Pitfalls.** Don't bake secrets into images; don't let the frontend talk to RunPod directly (all GPU
calls server-side for cost control + auth); pin dependency versions for reproducible event builds.

---

## Step 2 — Build the challenge engine

**Files to create**
| File | Purpose |
|------|---------|
| `backend/app/engine/challenge_engine.py` | Load YAML, seed per-session state, evaluate flag-release preconditions |
| `backend/app/engine/template_renderer.py` | `naive` (vulnerable) vs `structured` (fixed) prompt building |
| `backend/app/models/*.py`, `backend/app/schemas/*.py` | ORM + DTOs for sessions/attempts/solves |
| `challenges/_schema.md`, `challenges/level-0X.yaml` | Config format + the 9 challenge definitions |

**Recommended structure.**
```python
class ChallengeEngine:
    def load(self, cid: int) -> ChallengeConfig: ...
    def get_or_seed_session(self, user, cid) -> Session: ...      # rotating ids, planted memory, derived flag
    def render_input(self, cfg, session, fields) -> ModelInput: ...# delegates to template_renderer
    def check_release(self, cfg, session, signals) -> FlagDecision:...# precondition state machine
```
The **precondition state machine** is a declarative evaluator over `flag.release_conditions`; signals
(`tool_invoked`, `forged_role_seen`, `live_id_matches`) are emitted by the orchestrator during a turn
and accumulated on the session — this is what lets L8 accept multiple orderings.

**Technical decisions.** Config-as-data so `vulnerable`/`fixed` is a field flip, not a code branch
sprawl. Per-session derived flags (HMAC) so flag-sharing doesn't propagate solves. Seed RNG from
`session.seed` for reproducibility.

**Pitfalls.** Beware *unintended* solves — keep the state machine strict (AND of conditions) and
playtest. Don't leak derived flags into logs at INFO. Cache loaded configs but invalidate on
`mode` change (instructor may toggle for debrief).

---

## Step 3 — Build the prompt orchestration layer

**Files to create**
| File | Purpose |
|------|---------|
| `backend/app/engine/orchestrator.py` | Coordinate guardrails → render → image/model call → tools → output filter → release check |
| `backend/app/engine/guardrails/{base,denylist,classifier,stateful,output}.py` | Pluggable pre/post filters |
| `backend/app/engine/tools/{base,admin_tools}.py` | `describe_admin_config`, `run_admin_workflow` with optional authz gate |
| `backend/app/services/{imagegen,ocr,metadata}.py` | RunPod/mock client, OCR ingest (L7), metadata write/scrub |

**Recommended structure.**
```python
class Orchestrator:
    async def run_turn(self, cfg, session, fields) -> TurnResult:
        signals = Signals()
        fields = guardrails.pre(cfg, fields, signals)          # field-scoped per config (L3 gap)
        ctx    = ingest.ocr(fields.image) if cfg.ingest.ocr else None  # L7 indirect injection
        model_input = renderer.render(cfg, session, fields, ctx, signals) # detects forged roles → signals
        out = await imagegen.generate(model_input, session.seed)
        out = tools.maybe_invoke(cfg, model_input, session, signals)      # L7/L8 agency
        out = metadata.embed(out, cfg, session)                # verbose in L4
        out = guardrails.post(cfg, out, signals)               # weak/absent in vulnerable
        decision = engine.check_release(cfg, session, signals)
        return assemble(out, decision)
```
Guardrails implement a common `Filter` interface (`apply(fields|output, ctx) -> (modified, events)`).
The orchestrator is the single place signals are gathered, keeping the flaw surface auditable.

**Technical decisions.** All model I/O is async and time-bounded (RunPod timeouts → graceful error,
not a hang). The renderer *emits a `forged_role_seen` signal* when it detects delimiter injection —
the vuln is that it renders it anyway. OCR text is concatenated as "trusted context" only in
`vulnerable` mode (the teachable flaw).

**Pitfalls.** Don't let a guardrail exception fail open silently — log it. Bound OCR/image size
(DoS). Ensure tool invocation can't reach real infra — tools return *canned* per-session data only.
Time-box the model turn so one slow generate doesn't stall the room.

---

## Step 4 — Build the scoring engine

**Files to create**
| File | Purpose |
|------|---------|
| `backend/app/scoring/flag_validator.py` | Shape-check, constant-time compare, per-session derivation, anti-bruteforce |
| `backend/app/scoring/scoring_engine.py` | Idempotent first-solve scoring; rank decay; first-blood; Redis mirror |
| `backend/app/scoring/hint_engine.py` | Tiered hints, costs, auto-escalation |
| `backend/app/api/{submit,hints,scoreboard}.py` | Endpoints + WS |

**Recommended structure.** Submission flow: `validate shape → rate-limit check → derive expected →
constant-time compare → if correct & not already solved: transactionally insert solve (compute rank),
award points, mirror to Redis ZSET, publish WS`. See reference implementations in
[06-build-artifacts.md](06-build-artifacts.md#7-example-flag-validation-logic).

**Technical decisions.** Postgres is source of truth; Redis ZSET is a read cache for the live board.
Scoring is idempotent (unique key on `solves`) so double-submits and reconnects are safe. Rank-based
decay (not time) so RunPod cold-starts don't penalize.

**Pitfalls.** Race on first-blood: compute `solve_rank` inside the same transaction (`SELECT count
... FOR UPDATE` or a sequence per challenge). Don't reveal "close" on wrong flags (no oracle). Charge
hint cost *before* showing the hint text and make it idempotent per tier.

---

## Step 5 — Build the RunPod integration

**Files to create**
| File | Purpose |
|------|---------|
| `infra/runpod/handler.py` | Serverless handler: load pipeline + safety classifier, generate, return image + (verbose) metadata |
| `infra/runpod/Dockerfile.gpu`, `requirements.txt` | GPU image for the endpoint |
| `backend/app/services/imagegen.py` | Client: `runpod` and `mock` backends behind one interface |
| `scripts/loadtest.py` | Concurrency/latency test to size workers |

**Recommended structure.**
```python
# handler.py
def handler(event):
    p = event["input"]
    if not safety_classifier.ok(p["prompt"], p.get("negative_prompt","")):
        return {"error": "blocked_by_safety", "image": SAFE_PLACEHOLDER}   # immutable, out of scope
    img = pipe(prompt=p["prompt"], negative_prompt=p.get("negative_prompt"),
               num_inference_steps=p.get("steps", 4), seed=p["seed"]).images[0]
    return {"image_b64": to_b64(img), "provenance": build_provenance(p)}    # backend decides verbosity
```
Client uses the RunPod SDK with timeout + retry; `mock` returns a watermarked placeholder + synthetic
provenance so every challenge except raw aesthetics is developable offline.

**Technical decisions.** Few-step SDXL-Turbo/SD-1.5 for speed/cost. Pre-warm **active workers** before
CTF blocks; **scale-to-zero** + **max-workers ceiling** + **hard spend cap** as budget guardrails.
Safety classifier lives *in the handler* so it cannot be bypassed by any app-layer challenge.

**Pitfalls.** Cold-starts: pre-warm and surface a "warming up" UI state. Budget runaway: enforce the
spend cap + backend rate limits, not just the UI. Never return internal infra detail from the handler
except the *intended* provenance (which the backend, not the handler, decides to expose per
challenge). Keep the GPU image minimal to cut cold-start time.

---

## After Step 5

Proceed into Sprint 3–5 from [04-implementation-plan.md](04-implementation-plan.md): guardrail
`fixed`-mode counterparts, scoring/analytics dashboard, then the load-test + rehearsal + hardening
polish that makes it event-ready. Track the work via [github-project-board.md](github-project-board.md).
