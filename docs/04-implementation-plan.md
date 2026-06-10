# Phase 4 — Implementation Plan

Five sprints. Effort is in **engineer-days** (ideal). Assumes 1–2 engineers; a solo builder can run
sprints serially in ~4–5 weeks part-time. Each sprint ends shippable/demoable.

Legend — effort: S ≤1d, M 2–3d, L 4–5d.

---

## Sprint 1 — MVP (vertical slice)

**Goal:** a logged-in attendee can generate an image and submit a flag for *one* hardcoded
challenge, end to end. Proves the architecture and the RunPod path.

| Task | Effort | Notes |
|------|:--:|------|
| Repo scaffold, `docker-compose`, `.env.example`, CI lint/test | M | See [07](07-execution-roadmap.md) Step 1 |
| Postgres + Alembic baseline migration (core tables) | M | |
| Auth: access-code redeem → JWT; auth middleware | M | |
| `POST /api/generate` happy path → mock imagegen → response | M | Mock first; no GPU dependency |
| RunPod serverless handler + client (behind `IMAGEGEN_MODE`) | L | SDXL-Turbo image; safety classifier wired in |
| Minimal React SPA: login, one challenge, prompt box, image, flag submit | L | |
| Flag validator (static flag) + idempotent solve record | S | |

**Deliverables:** running compose stack; one playable challenge (Level 1) on mock + real RunPod;
flag submission scores.
**Dependencies:** RunPod account + endpoint (for the real path); domain optional.
**Exit criteria:** demo Level 1 solve locally and against RunPod.

---

## Sprint 2 — Challenge engine

**Goal:** challenges become **config-driven**; all 8 levels load from YAML; per-session seeding and
precondition state machine work.

| Task | Effort | Notes |
|------|:--:|------|
| Challenge YAML schema + loader + validation | M | `challenges/level-NN.yaml` |
| Per-session seeding (`rotating_state`, derived flags, planted memory) | M | |
| Precondition state machine for flag release | L | Powers L8 multi-condition |
| Template renderer with `vulnerable|fixed` modes | M | Naive interpolation vs. structured |
| Tool framework + challenge-exposed tools (`describe_admin_config`, `run_admin_workflow`) | M | L7/L8 |
| Multi-turn session memory (Redis) + conversation API | M | L6/L8 |
| Image upload + OCR ingest path | M | L7 indirect injection |
| Metadata writer (verbose provenance) | S | L4 |
| Author all 8 challenge YAMLs + per-challenge flags | L | The actual content |
| Challenge unlock ordering / dependency gating | S | |

**Deliverables:** all 8 challenges playable end-to-end in vulnerable mode.
**Dependencies:** Sprint 1.
**Exit criteria:** internal playtest solves every level via its expected path.

---

## Sprint 3 — Guardrail framework

**Goal:** pluggable guardrails so each challenge demonstrates a *specific* defensive gap, and a
`fixed` mode that actually closes it (for the debrief).

| Task | Effort | Notes |
|------|:--:|------|
| Guardrail interface (pre/post hooks) + pipeline runner | M | |
| Denylist filter; field-scoped (the L3 "prompt-only" gap) | S | |
| Lightweight classifier guardrail (policy intent) | M | Small model or heuristic |
| Per-turn vs. stateful (whole-conversation) guardrail | M | L6 contrast |
| Output filter (response + metadata scrubber for `fixed` mode) | M | |
| Structured-prompt renderer for `fixed` mode (template-injection fix) | M | |
| Tool authorization gate for `fixed` mode | S | L7/L8 fix |
| `fixed`-mode regression tests (each level becomes unexploitable) | L | Proves the mitigations |

**Deliverables:** every challenge has a working `fixed` counterpart for debriefs; guardrail configs
documented.
**Dependencies:** Sprint 2.
**Exit criteria:** automated test shows each level solvable in `vulnerable` and *blocked* in `fixed`.

---

## Sprint 4 — Scoring & analytics

**Goal:** competitive scoring, live scoreboard, hint economy, and the instructor dashboard.

| Task | Effort | Notes |
|------|:--:|------|
| Scoring engine (base − hints − decay + first-blood + writeup) | M | |
| Redis scoreboard sorted-set + WS live updates | M | |
| Hint engine: tiers, costs, auto-escalation | M | |
| Writeup submission + judging hooks (L8) | S | |
| Prometheus metrics + Loki structured logging | M | |
| Grafana instructor dashboard + stuck heatmap | L | |
| Admin controls API (mock failover, broadcast hint, reset session, kill account) | M | |
| Anti-abuse: submission rate limit/backoff/lockout | S | |

**Deliverables:** full scoreboard, hint economy, instructor dashboard with live controls.
**Dependencies:** Sprints 2–3.
**Exit criteria:** dry-run with 5 testers shows live scoring, hints, and dashboard accuracy.

---

## Sprint 5 — Workshop polish

**Goal:** event-ready. Load-tested, documented, failure-resilient, pretty enough to project.

| Task | Effort | Notes |
|------|:--:|------|
| Load test 50–100 concurrent generates; tune RunPod max-workers + active pre-warm | L | Use [cost-estimate.md](cost-estimate.md) numbers |
| RunPod→mock auto-failover + budget alarm | M | |
| UI polish: metadata inspector, "copy as request", conversation pane, scoreboard projector mode | L | |
| Level 0 smoke-test + onboarding flow | S | |
| Content: instructor/student guides finalized, hint copy review, award flow | M | |
| Pre-generated access codes + check-in export | S | |
| Full run-of-show rehearsal (timed) | M | With volunteers |
| Hardening pass against the platform threat model (§13) | M | |
| `fixed`-mode debrief walkthrough screencasts (backup demos) | S | |

**Deliverables:** rehearsed, load-tested, documented workshop ready to run at 50 attendees with
100-attendee headroom.
**Dependencies:** Sprints 1–4.
**Exit criteria:** timed rehearsal completes within 3h; failover tested; cost within budget.

---

## Cross-sprint workstreams

- **Security of the platform** (threat model §13): a little each sprint, hardening pass in S5.
- **Docs**: keep `docs/` current; they are deliverables, not afterthoughts.
- **Playtesting**: every sprint from S2 ends with a playtest; bugs feed the next sprint.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|:--:|:--:|------|
| RunPod cold-starts under load | M | M | Active worker pre-warm; mock failover; rank-based score decay |
| A challenge has an unintended easy solve | M | L | Playtest each sprint; precondition state machine; alt-path notes |
| Budget overrun | L | M | Hard spend cap, rate limits, scale-to-zero, alarms |
| Attendees attack platform not target | L | M | Threat model controls; clear rules of engagement |
| Image model emits unsafe content | L | H | Immutable safety classifier; flags never require harmful output |
