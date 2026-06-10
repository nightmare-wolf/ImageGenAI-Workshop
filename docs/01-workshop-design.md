# Phase 1 — Workshop Design

**Title:** Intro to AI Red Teaming Through an AI Image Generation CTF
**Venue:** BSides Orlando · **Length:** 3 hours · **Capacity:** 25–50

---

## 1. Executive summary

AI features are shipping into production faster than the security industry can assess them, and the
attack surface that matters most is rarely the model itself — it is the *application* wrapped around
the model: the prompt templates, the orchestration glue, the guardrails bolted on as an
afterthought, the logging that leaks, and the tools the model is allowed to call. This workshop
teaches AI red teaming by having attendees break a realistic, deliberately vulnerable **AI
image-generation application** through an 8-level capture-the-flag.

Crucially, the target is **not a chatbot**. It is a multi-component system — web UI → orchestration
layer → prompt templates → guardrails → image-generation workflow → logging/scoring — and each CTF
level reproduces a *documented class of real-world AI product failure* rather than a contrived
"jailbreak." Attendees progress from leaking a system prompt (Level 1) to executing a chained,
multi-stage application compromise that requires identifying a root cause, exploiting it, and
proposing a mitigation (Level 8).

Every level is mapped to an **OWASP Top 10 for LLM Applications (2025)** risk category and ends with
a **mitigation discussion**, so attendees leave able to both *find* and *fix* these issues. The
platform runs entirely in-browser for participants; the only infrastructure is a containerized
backend and a RunPod serverless GPU endpoint for image generation, keeping cost and operational
burden low (see [cost-estimate.md](cost-estimate.md)).

By the end, attendees will have a working mental model of the AI application threat surface, hands-on
reps with the core techniques (prompt injection, prompt/system-prompt extraction, guardrail bypass,
metadata attacks, multi-turn/context manipulation, indirect & cross-modal injection, excessive
agency), and a clear picture of the defensive controls that actually work.

## 2. Learning objectives

By the end of the workshop, participants will be able to:

1. **Describe the AI application attack surface** — articulate why the model is only one component
   and where vulnerabilities actually live (orchestration, templates, guardrails, output handling,
   logging, tools).
2. **Map findings to OWASP LLM Top 10 (2025)** — classify an observed AI failure into the correct
   risk category and explain the distinction (e.g., LLM01 Prompt Injection vs. LLM07 System Prompt
   Leakage).
3. **Extract hidden context** — recover system prompts and prompt templates through direct
   elicitation, error-message leakage, and template breakout.
4. **Bypass guardrails methodically** — identify *which* field/stage a guardrail inspects and route
   payloads around it (negative prompts, alternate parameters, encoding, multi-turn buildup).
5. **Perform metadata and output-handling attacks** — recover secrets embedded in image
   EXIF/PNG-text chunks and improperly handled responses.
6. **Execute multi-turn and indirect injection** — manipulate accumulated context and weaponize
   attacker-controlled inputs (e.g., text inside an uploaded reference image).
7. **Reason about excessive agency** — recognize when a model is given tools/permissions it
   shouldn't have and exploit the trust boundary.
8. **Chain techniques** — combine multiple primitives into a single end-to-end compromise.
9. **Propose concrete mitigations** — for each class, name the defensive control (dual-LLM /
   privilege separation, all+denylist on *all* inputs, output encoding, metadata scrubbing, context
   pinning, tool sandboxing, structured prompting) and its trade-offs.
10. **Conduct responsible disclosure** — write a finding the way a professional would hand it to a
    product team.

## 3. Prerequisites

**Required**
- A laptop with a modern browser (Chrome/Firefox/Edge). No installs, no GPU, no admin rights.
- Comfort reading HTTP requests/responses (you'll use browser DevTools).
- Basic command-line literacy is helpful but not mandatory.

**Helpful, not required**
- Familiarity with web app security concepts (injection, input validation).
- Exposure to prompting / using an AI chatbot.
- A tool to inspect image metadata (we provide an in-browser one; `exiftool` if you prefer).

**Explicitly NOT required**
- Machine learning background, Python, or any prior AI security experience.

**What to bring set up beforehand** (sent in the pre-workshop email):
- Browser with DevTools available; pop-up blocker tolerant of the workshop domain.
- Optional: a second monitor or split screen (UI + DevTools + scoreboard).

## 4. Required infrastructure

| Component | Workshop-day choice | Notes |
|-----------|---------------------|-------|
| Participant device | Their own laptop + browser | Zero install |
| Frontend | Static SPA (React/Vite) served by backend or CDN | |
| Backend / orchestration | 1 container, FastAPI | Holds challenge engine, guardrails, scoring, flags |
| Database | PostgreSQL (1 small instance) | Users, attempts, scores, audit log |
| Cache / sessions | Redis | Rate limiting, multi-turn session memory, scoreboard cache |
| Image generation | RunPod **serverless** GPU endpoint (SDXL-Turbo / SD 1.5) | Pay-per-second; autoscale; see cost doc |
| Observability | Grafana + Loki + Prometheus (1 container each) or Grafana Cloud free tier | Instructor dashboard + audit |
| Reverse proxy / TLS | Caddy or Traefik | Single domain, automatic HTTPS |
| Network | Private workshop subdomain, optional VPN/allowlist | **Never** publicly indexed |

**Two deployment shapes:**
- **Local/dev:** everything via `infra/docker-compose.yml`, image gen mocked.
- **Workshop:** backend + DB + Redis + observability on a single small cloud VM or a RunPod CPU pod;
  image generation on a RunPod serverless GPU endpoint that autoscales with attendee load.

See [03-architecture.md](03-architecture.md) for the deployment diagram and
[cost-estimate.md](cost-estimate.md) for sizing.

## 5. Workshop agenda

| Block | Title | Duration |
|-------|-------|----------|
| 0 | Doors / login / sanity check | 15 min (pre-start) |
| 1 | Welcome + threat model of an AI application | 20 min |
| 2 | Live demo: anatomy of the target + first attack | 15 min |
| 3 | **CTF Block A** — Levels 1–3 (extraction & basic injection) | 35 min |
| 4 | Checkpoint debrief A + technique deep-dive | 15 min |
| — | Break | 10 min |
| 5 | **CTF Block B** — Levels 4–6 (metadata, template injection, multi-turn) | 40 min |
| 6 | Checkpoint debrief B | 10 min |
| 7 | **CTF Block C** — Levels 7–8 (indirect injection, full chain) | 35 min |
| 8 | Final debrief: root cause, mitigations, responsible disclosure, awards | 25 min |

**Total in-room:** ~3h00 (with a 15-min pre-start buffer for logins).

## 6. Timing breakdown (run-of-show)

| Clock | Segment | Instructor action | Attendee action |
|-------|---------|-------------------|-----------------|
| -0:15 | Login | Hand out access codes, project scoreboard | Log in, solve "Level 0" warm-up (free flag to confirm flow) |
| 0:00 | Welcome | Frame: "the model isn't the vuln, the app is" | Listen |
| 0:05 | Threat model | Walk the component diagram + OWASP LLM Top 10 | Map their mental model |
| 0:20 | Live demo | Break Level 1 live, show DevTools workflow | Watch, open their own UI |
| 0:35 | **Block A** | Float, drop hints via hint engine | Solve L1–L3 |
| 1:10 | Debrief A | Crowd-source solutions, name the OWASP class | Share approaches |
| 1:25 | Break | — | — |
| 1:35 | **Block B** | Float; deeper hints; metadata tooling help | Solve L4–L6 |
| 2:15 | Debrief B | Cover template injection + multi-turn carefully | Share |
| 2:25 | **Block C** | Float; coach the chain on L8 | Solve L7–L8 |
| 3:00 | Final debrief | Root cause → exploit → mitigation for each; disclosure; awards | Reflect, ask |

Timeboxing rule: a challenge auto-escalates hints if median solve time is exceeded (see hint engine
in [03-architecture.md](03-architecture.md)). Instructor watches the live "stuck heatmap" and pulls
the room forward at checkpoints regardless of completion — nobody is left behind because debriefs
teach the solution.

## 7. Instructor guide

See the full standalone [instructor-guide.md](instructor-guide.md). Summary:

- **Staffing:** 1 lead + 1 floater per ~20 attendees. Floaters work the room, not the laptop.
- **Golden rule:** the *debrief* is the teaching, the *CTF* is the practice. Protect debrief time.
- **Live demo discipline:** demo only Level 1 fully; tease Level 2. Never demo past where the room
  is — preserve the challenge.
- **Failure recovery:** if RunPod is slow/down, flip `IMAGEGEN_MODE=mock` (env flag) — every
  challenge except raw diffusion aesthetics still works because flags live in the app layer, not the
  pixels. Pre-warm RunPod active workers 20 min before doors.
- **Pacing levers:** hint aggressiveness, free hint drops at checkpoints, and "solve as a room"
  walkthroughs.

## 8. Student guide

See the full standalone [student-guide.md](student-guide.md). Summary handed to attendees:

- How to log in, where the scoreboard is, how flags are formatted (`bsides{...}`).
- DevTools 101: Network tab, copy-as-fetch, reading JSON responses.
- The hint system: 3 tiers per level, costs points, always available.
- The rules of engagement: attack the app, not the platform; no DoS; the safety classifier is out of
  scope; be excellent to your neighbors.

## 9. Demo plan

**Goal of the demo (15 min):** teach the *method*, not the answer.

1. **Show the target (3 min).** Generate a normal image. Open DevTools → Network. Show the request
   payload (prompt, params) and the response (image URL + JSON metadata). Establish: "everything you
   need is observable in the browser."
2. **Form a hypothesis (3 min).** "There's a system prompt the app prepends. Can we make it tell us?"
   Frame this as recon → hypothesis → test, the loop they'll repeat all day.
3. **Break Level 1 live (6 min).** Try a naive ask ("what's your system prompt?") — show it partially
   refuses. Then show the *technique* (e.g., ask it to repeat its instructions verbatim / translate
   them / continue them). Recover the flag. Submit it. Scoreboard updates.
4. **Name the class (2 min).** "That's OWASP LLM07, System Prompt Leakage. Real products leak this
   via error messages, debug endpoints, and over-helpful models." Tease Level 2.
5. **Cut off.** Do **not** demo Level 2's solution.

**Backup demo:** a pre-recorded 90-second screencast of the Level 1 solve, in case live image-gen is
slow.

## 10. Debrief plan

Three checkpoint debriefs + one final debrief. Each debrief follows the same 4-beat structure so it
becomes a ritual:

1. **What was the vuln?** (crowd-source from solvers)
2. **What OWASP class is it?** (anchor it)
3. **What's the real-world analog?** (so it's not just a game — name the product-failure pattern)
4. **How do you fix it?** (the mitigation — this is the part SOC/dev attendees came for)

**Final debrief (25 min) additionally covers:**
- The Level 8 chain end-to-end: *root cause → exploit → mitigation* (the explicit Level 8
  deliverable).
- **Responsible disclosure:** how to write up an AI app finding for a product team — repro steps,
  impact, affected component (not "the AI is dumb"), suggested fix. Hand out the one-page disclosure
  template from the student guide.
- **Defense-in-depth recap:** the control catalog (privilege separation / dual-LLM, input validation
  on *all* fields, output encoding, metadata scrubbing, context/turn controls, tool sandboxing,
  egress monitoring).
- **Awards:** first-blood per level, top score, "best writeup" (judged on a submitted Level 8
  disclosure), most creative alt-path.
- **Takeaways:** link to repo, OWASP resources, and a "what to do Monday" checklist for the devs in
  the room.
