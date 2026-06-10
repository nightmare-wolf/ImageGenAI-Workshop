# Instructor Guide

Everything the lead + floaters need to run the 3-hour workshop. Pair with the run-of-show in
[01-workshop-design.md](01-workshop-design.md#6-timing-breakdown-run-of-show).

## Philosophy

> **The CTF is the practice. The debrief is the teaching.** Protect debrief time at all costs — a
> half-solved room that gets a great debrief learns more than a fully-solved room that runs out of
> clock. Nobody is "behind": every solution is taught at the checkpoint.

## Staffing & roles

- **1 Lead** — runs the front, demo, debriefs, watches the dashboard, makes pacing calls.
- **1 Floater per ~20 attendees** — works the room, unblocks people *with questions, not answers*
  ("what does DevTools show you?" not "put it in the negative prompt"). Floaters never touch an
  attendee's keyboard.
- **1 Ops** (can be the Lead at small scale) — owns RunPod health, failover, budget alarm.

## Pre-flight checklist (T-60 min)

- [ ] Backend, DB, Redis, observability stack healthy (Grafana green).
- [ ] RunPod endpoint reachable; **pre-warm active workers** (T-20).
- [ ] `IMAGEGEN_MODE=runpod`; mock failover tested once.
- [ ] Scoreboard projector view up; Level 0 smoke test solvable.
- [ ] Access codes printed/handed out; check-in sheet ready.
- [ ] Backup demo screencast loaded; this guide + student guide on hand.
- [ ] Network: workshop subdomain resolves on conference Wi-Fi from a test laptop.

## Talk track — opening (20 min)

1. **Hook (2m):** "The model is the part everyone fixates on. It's almost never where the bug is.
   Today you'll break the *application* around the model."
2. **Threat model (10m):** walk the component diagram ([03](03-architecture.md#1-system-overview)).
   Land the line: *anything you send to the model can come back; any field that reaches the model is
   an input you must validate; any output channel — including image metadata — can leak.*
3. **OWASP framing (5m):** show the [mapping](owasp-mapping.md). "Each level is a real failure class,
   and each ends with the fix — because half of you are here to *build* these, not just break them."
4. **Rules of engagement (3m):** attack the target app, not the platform; no DoS; the safety
   classifier is out of scope and flags never require harmful content; help your neighbors at
   checkpoints.

## Live demo (15 min) — Level 1 only

Follow [01 §9 Demo plan](01-workshop-design.md#9-demo-plan). Teach the *loop* (recon → hypothesize →
test → read response/metadata). Solve Level 1, name LLM07, **stop**. Do not demo Level 2+.

## Running the CTF blocks

- Watch the **stuck heatmap**. If median solve-time on a level is exceeded by most of the room,
  broadcast a free Tier-1 hint.
- Float, don't hover. Ask questions. Celebrate first-bloods out loud (cheap motivation).
- At each checkpoint, **pull the room forward regardless of completion** — the debrief catches
  everyone up.

## The debrief ritual (every checkpoint)

Run the same 4 beats so it becomes muscle memory:
1. **What was the vuln?** (a solver explains)
2. **What OWASP class?** (you anchor it)
3. **Real-world analog?** (name the product-failure pattern from [02](02-ctf-design.md))
4. **The fix?** (the mitigation — show `fixed` mode breaking the same attack live if time allows)

### Block A debrief (L1–L3)
System-prompt-as-config; instructions ≠ authorization; *validate every field*. Show DevTools request
body so the L3 lesson sticks.

### Block B debrief (L4–L6)
Metadata is an output channel (open an image's `tEXt` chunks live); template injection = the LLM-era
SQL-injection (structured roles vs. string interpolation); per-turn guardrails miss multi-turn —
guardrails must see the whole conversation.

### Final debrief (L7–L8, 25 min)
- Indirect/cross-modal injection: *your inputs can carry someone else's instructions*; excessive
  agency = tools without authz.
- **Walk the Level 8 chain end-to-end: root cause → exploit → mitigation.** Emphasize the root cause
  is *patches that don't compose*, not any single bug.
- **Responsible disclosure (5m):** hand out the one-page template; show a good vs. bad writeup.
- **Awards:** first-bloods, top score, best writeup, most creative alt-path.
- **"Monday" checklist** for the builders in the room (control catalog, [03 §14](03-architecture.md#14-security-controls-catalog-what-we-teach-as-the-fixes)).

## Failure recovery playbook

| Symptom | Action |
|---------|--------|
| RunPod slow / cold-start storm | Confirm active workers warm; if persists, `POST /api/admin/imagegen-mode {mock}` — everything but raw aesthetics still works |
| RunPod down / over budget | Flip to `mock`; announce "image fidelity is degraded, all challenges still solvable" |
| Live demo image won't generate | Play the backup screencast; narrate over it |
| One challenge has a flood of stuck attendees | Broadcast next hint tier; if a bug, freeze that challenge and move on |
| Disruptive/abusive account | `POST /api/admin/lock-user`; reset if accidental |
| Scoreboard wedged | It's a cache — restart backend; Postgres is source of truth, no data lost |

## Pacing levers (in priority order)

1. Broadcast hints. 2. "Solve it as a room" walkthrough of the current level. 3. Shorten the next
block and lengthen its debrief. 4. Drop the optional alt-path discussion. Never skip a debrief.
