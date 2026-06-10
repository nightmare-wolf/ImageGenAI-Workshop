# Security & Safety Policy

This repository contains a **deliberately vulnerable** AI image-generation application built for
authorized AI security *education*. Read this before deploying.

## Intended use

For instructor-led workshops, classrooms, and personal AI-security study only. The vulnerabilities
are intentional and confined to the *target application behavior* (`mode: vulnerable` in challenge
configs) — the orchestration, template, guardrail, and tool layers. They do **not** grant access to
the host, the scoring database, or other participants (see the platform threat model in
[`docs/03-architecture.md`](docs/03-architecture.md#13-threat-model)).

## Deployment rules

- **Never expose this to the public internet** without the workshop network controls (private
  subdomain, access codes, rate limits, budget caps). It is not hardened for hostile public traffic.
- Run it ephemerally; tear down and purge data after the event.
- Keep `SECRET_KEY` and `SERVER_SECRET` out of source control and rotate per event.

## Hard safety boundaries (non-negotiable)

- A **NSFW/CSAM safety classifier** wraps every image generation, lives in the RunPod handler, and is
  **out of scope** for all challenges. No challenge requires — or rewards — generating harmful,
  explicit, or illegal content. **Do not disable it.**
- No flag is ever hidden behind producing harmful content.
- The platform collects **no PII** (access codes only). Logs are gameplay telemetry and are purged
  after the event.

## What this is NOT for

Malware creation, harmful content generation, attacking systems you don't own, or any real-world
abuse. The skills taught are for defensive AI security and authorized red teaming.

## Reporting issues with the platform itself

If you find a vulnerability in the *platform* (scoring, auth, isolation) — as opposed to an intended
*challenge* vuln — open a private security advisory on the repo or contact the maintainers. Please
don't file intended challenge behavior as a bug.
