# GitHub Project Board — Epics → Stories → Tasks

Structure for a GitHub Projects (v2) board. Use **Epics** as labels/milestones, **Stories** as
issues, **Tasks** as issue checklists or sub-issues. Suggested board columns: `Backlog → Ready →
In Progress → Review → Done`. Map Epics to the five sprints in
[04-implementation-plan.md](04-implementation-plan.md).

Suggested labels: `epic:*`, `area:backend|frontend|infra|content|security`, `sprint:1..5`,
`type:feat|chore|bug|docs`, `good-first-issue`.

---

## EPIC 1 — Platform Foundation (Sprint 1)

- **Story 1.1 — Repo & CI scaffold**
  - [ ] Init repo, `.gitignore`, `.env.example`, LICENSE, SECURITY.md
  - [ ] `docker-compose.yml` (postgres, redis, backend, frontend, caddy)
  - [ ] CI: lint (ruff/eslint), type-check (mypy/tsc), unit test gate
- **Story 1.2 — Datastore**
  - [ ] Alembic baseline migration (core tables)
  - [ ] Seed script (challenges, demo access codes)
- **Story 1.3 — Auth**
  - [ ] `gen_access_codes.py`; redeem endpoint → JWT; auth middleware; role claims
- **Story 1.4 — Generate happy path (mock)**
  - [ ] `POST /api/generate` → mock imagegen → response
  - [ ] Mock image service (watermarked placeholder + synthetic provenance)
- **Story 1.5 — RunPod path**
  - [ ] Serverless handler + GPU Dockerfile; SDXL-Turbo pipeline; safety classifier
  - [ ] `imagegen.py` client behind `IMAGEGEN_MODE`
- **Story 1.6 — Minimal SPA**
  - [ ] Login, single challenge, prompt box, image render, flag submit

## EPIC 2 — Challenge Engine (Sprint 2)

- **Story 2.1 — Config system**
  - [ ] YAML schema + loader + validation; `_schema.md`
  - [ ] `vulnerable|fixed` mode switch
- **Story 2.2 — Session seeding & flags**
  - [ ] Per-session `rotating_state`, derived (HMAC) flags, planted memory
- **Story 2.3 — Precondition state machine**
  - [ ] Declarative `release_conditions` evaluator; signal accumulation
- **Story 2.4 — Template renderer**
  - [ ] `naive` interpolation; delimiter/role handling; forged-role detection signal
- **Story 2.5 — Tools & multimodal ingest**
  - [ ] Tool framework; `describe_admin_config`, `run_admin_workflow`
  - [ ] Image upload + OCR ingest (L7)
- **Story 2.6 — Multi-turn**
  - [ ] Redis session memory + conversation API (L6/L8)
- **Story 2.7 — Metadata writer** (L4 verbose provenance)
- **Story 2.8 — Author all 9 challenge YAMLs** (L0–L8) + internal playtest

## EPIC 3 — Guardrail Framework (Sprint 3)

- **Story 3.1 — Pipeline & interface** (pre/post hooks)
- **Story 3.2 — Filters** (denylist field-scoped; classifier; stateful/whole-conversation)
- **Story 3.3 — Output controls** (response filter + metadata scrubber for `fixed`)
- **Story 3.4 — Structured-prompt renderer** (`fixed` template-injection fix)
- **Story 3.5 — Tool authz gate** (`fixed` LLM06 fix)
- **Story 3.6 — Fixed-mode regression suite** (each level unexploitable in `fixed`)

## EPIC 4 — Scoring & Analytics (Sprint 4)

- **Story 4.1 — Scoring engine** (base − hints − decay + first-blood + writeup; idempotent)
- **Story 4.2 — Live scoreboard** (Redis ZSET + WS; projector mode)
- **Story 4.3 — Hint engine** (tiers, costs, auto-escalation, broadcast)
- **Story 4.4 — Writeup submission + judging** (L8)
- **Story 4.5 — Observability** (Prometheus metrics, Loki logs, audit stream)
- **Story 4.6 — Instructor dashboard** (solve counts, stuck heatmap, RunPod health/spend)
- **Story 4.7 — Admin controls API** (mock failover, broadcast, reset, lock)
- **Story 4.8 — Anti-abuse** (submission rate limit/backoff/lockout)

## EPIC 5 — Workshop Polish (Sprint 5)

- **Story 5.1 — Load test & RunPod tuning** (50–100 concurrent; active pre-warm; max-workers)
- **Story 5.2 — Failover & budget alarm** (RunPod→mock; spend cap)
- **Story 5.3 — UI polish** (metadata inspector, copy-as-request, conversation pane, scoreboard)
- **Story 5.4 — Onboarding** (Level 0 smoke test, login flow, check-in)
- **Story 5.5 — Content finalization** (instructor/student guides, hint copy, awards)
- **Story 5.6 — Access codes & check-in export**
- **Story 5.7 — Timed rehearsal** (full run-of-show with volunteers)
- **Story 5.8 — Platform hardening pass** (threat model §13)
- **Story 5.9 — Backup demo screencasts** (`fixed`-mode debrief walkthroughs)

---

### Milestones
`M1 MVP` · `M2 All challenges playable` · `M3 Fixed-mode + guardrails` · `M4 Scoring/dashboard` ·
`M5 Event-ready (rehearsed + load-tested)`.

### Definition of Done (every story)
Code + tests pass CI · docs updated · playtested where user-facing · no secrets committed · respects
platform threat model.
