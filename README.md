# Intro to AI Red Teaming Through an AI Image Generation CTF

> A BSides Orlando workshop + buildable, deliberately-vulnerable AI image-generation
> application used to teach AI red teaming through a progressive, 8-level CTF.

**Audience:** security professionals, pentesters, SOC analysts, students, developers, and AI-curious hackers.
**Format:** 3-hour hands-on workshop, 25–50 attendees, browser-only for participants.
**Goal:** Teach AI application security — not "jailbreak golf" — by reproducing *real-world AI
application failures* as CTF challenges, each mapped to an OWASP LLM/GenAI risk category, each
with a required mitigation discussion.

---

## What makes this different

This is **not** an LLM chatbot CTF. The target is a full **AI application**: a web frontend, an
orchestration layer, prompt templates, guardrails, image-generation workflows, logging, scoring,
and flags. Vulnerabilities are deliberately seeded at the *application boundaries* — the same
places real products get owned — not in the model weights.

Every challenge is modeled on a documented class of real-world AI product failure (system-prompt
leakage, single-field input validation, metadata over-disclosure, template injection, multi-turn
context erosion, indirect/cross-modal injection, excessive tool agency).

## Repository map

| Path | What it is |
|------|------------|
| [`docs/01-workshop-design.md`](docs/01-workshop-design.md) | **Phase 1** — exec summary, objectives, prerequisites, infra, agenda, timing, demo, debrief |
| [`docs/02-ctf-design.md`](docs/02-ctf-design.md) | **Phase 2** — 8 challenge levels, full design each |
| [`docs/03-architecture.md`](docs/03-architecture.md) | **Phase 3** — frontend/backend/db/auth/scoring/logging/flag/challenge/hint/admin + diagrams, data flow, threat model |
| [`docs/04-implementation-plan.md`](docs/04-implementation-plan.md) | **Phase 4** — 5 sprints (tasks, deliverables, dependencies, effort) |
| [`docs/05-tech-stack.md`](docs/05-tech-stack.md) | **Phase 5** — stack recommendations + the *why* for each |
| [`docs/06-build-artifacts.md`](docs/06-build-artifacts.md) | **Phase 6** — dir structure, schema, API, challenge format, compose, examples |
| [`docs/07-execution-roadmap.md`](docs/07-execution-roadmap.md) | **Phase 7** — actionable, file-by-file build roadmap |
| [`docs/owasp-mapping.md`](docs/owasp-mapping.md) | Challenge → OWASP LLM Top 10 (2025) risk mapping |
| [`docs/cost-estimate.md`](docs/cost-estimate.md) | RunPod cost models for 25 / 50 / 100 attendees |
| [`docs/github-project-board.md`](docs/github-project-board.md) | Epics → Stories → Tasks board structure |
| [`docs/instructor-guide.md`](docs/instructor-guide.md) | Run-of-show, talk track, failure recovery |
| [`docs/student-guide.md`](docs/student-guide.md) | Participant handout (browser-only) |
| `backend/` | FastAPI orchestration + challenge/scoring/flag/hint engines (scaffold) |
| `frontend/` | React + Vite + Tailwind play UI (scaffold) |
| `challenges/` | YAML challenge definitions (`level-01.yaml` … `level-08.yaml`) |
| `infra/` | Docker, Compose, RunPod handler, observability config |

## Quick start (local dev)

```bash
cp .env.example .env            # fill in secrets
docker compose -f infra/docker-compose.yml up --build
# frontend  -> http://localhost:5173
# backend   -> http://localhost:8000/docs
# grafana   -> http://localhost:3000
```

For the GPU image backend you either point `RUNPOD_ENDPOINT_ID` at a RunPod serverless endpoint
(production / workshop day) or run the local `mock-imagegen` container (no GPU, returns watermarked
placeholder images — good enough to develop every challenge except real diffusion output).

## Safety & legality

This platform is for **authorized AI security education only**. It deliberately contains
vulnerabilities; **never expose it to the public internet without the workshop network controls
described in [`docs/03-architecture.md`](docs/03-architecture.md).** The image model is configured
with a hard NSFW/CSAM safety classifier that is **out of scope** for all challenges and must never
be disabled — flags are never hidden behind generating harmful content. See
[`SECURITY.md`](SECURITY.md).

## License

MIT for the platform code. Workshop content (docs/) is CC BY-SA 4.0. See [`LICENSE`](LICENSE).
