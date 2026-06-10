# Challenge Configuration Schema

Every file `challenges/level-NN.yaml` is validated against this schema by
`backend/app/engine/challenge_engine.py` on load. The same engine renders **vulnerable** or
**fixed** behavior purely from these fields — flip `mode` for debriefs.

| Field | Type | Required | Description |
|-------|------|:--:|-------------|
| `id` | int (0–8) | ✔ | Stable challenge id |
| `slug` | string | ✔ | URL-safe identifier |
| `name` | string | ✔ | Display name |
| `owasp_tag` | `LLM01`…`LLM10` \| `chained` | ✔ | Primary OWASP category |
| `difficulty` | int 1–5 | ✔ | Star rating |
| `base_points` | int | ✔ | Pre-hint, pre-decay score |
| `depends_on` | int[] | ✔ | Challenges that must be solved first (unlock order) |
| `mode` | `vulnerable` \| `fixed` | ✔ | Behavior toggle |
| `story` | string | ✔ | Player-facing narrative |
| `system_prompt` | string | ✔ | Prepended instruction (may embed a flag for LLM07) |
| `template.mode` | `naive` \| `structured` | ✔ | `naive` = string interpolation (vulnerable); `structured` = typed roles (fixed) |
| `template.delimiters` | map | – | Role delimiter tokens used in `naive` mode |
| `template.body` | string | ✔ | Template with `{placeholders}` |
| `internal_directives` | string | – | Server-only variable (LLM05/template target) |
| `guardrails.pre` | filter[] | ✔ | Input filters. Each: `{type, fields}`. **Field-scoping is the L3 vuln.** |
| `guardrails.post` | filter[] | ✔ | Output filters (empty/weak = vulnerable) |
| `tools` | string[] | – | Tools exposed to the model this challenge (`describe_admin_config`, `run_admin_workflow`) |
| `ingest.ocr` | bool | – | If true, OCR uploaded images and feed text to the prompt (L7 indirect injection) |
| `metadata.verbosity` | `verbose` \| `minimal` | ✔ | `verbose` embeds internals in the image (L4) |
| `seed_state.rotating` | string[] | – | Per-session values to generate (e.g. `admin_workflow_id`) |
| `seed_state.planted_memory` | turn[] | – | Conversation turns pre-seeded into session memory (L6) |
| `flag.type` | `static` \| `derived` | ✔ | `derived` = per-session HMAC token |
| `flag.value` | string | for static | The literal flag |
| `flag.release_conditions` | condition[] | for chained | Declarative preconditions; **all** must hold (L8) |
| `hints` | hint[] | ✔ | `{tier, cost, text}` × 3 |
| `mitigation` | string | ✔ | Debrief talking points (the fix) |

### Filter types (`guardrails.*[].type`)
`denylist` (string/regex match), `classifier` (policy-intent model/heuristic), `stateful`
(whole-conversation scoring), `output_scan` (sensitive-string scan on response), `metadata_scrub`
(strip provenance). Each takes `fields: [...]` to scope which inputs/outputs it inspects.

### Release conditions (`flag.release_conditions[]`)
Signals emitted by the orchestrator during a turn and accumulated on the session:
`tool_invoked: <name>`, `forged_role_seen: true`, `live_id_matches: true`,
`turn_count_at_least: <n>`, `field_carried_payload: <field>`. The challenge engine releases the flag
only when **every** listed condition is satisfied (logical AND), which is what makes Level 8 require
the full chain while still accepting different orderings.

### Mode semantics
- `vulnerable`: `template.mode=naive`, narrow `guardrails`, `metadata.verbosity=verbose`, tools
  ungated.
- `fixed`: `template.mode=structured`, full-coverage guardrails + `output_scan`/`metadata_scrub`,
  tools authorization-gated. Used in debriefs to show the same attack failing.
