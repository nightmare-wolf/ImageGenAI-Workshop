# Phase 6 — Build Artifacts

Concrete, ready-to-use artifacts. Many of these also exist as real files in the repo (see paths);
this document is the canonical reference.

---

## 1. Project directory structure

```
ImageGenAI-Workshop/
├── README.md  SECURITY.md  LICENSE  .env.example  .gitignore
├── docs/                         # Phases 1–7 + guides + mappings + costs
├── challenges/                   # one YAML per level
│   ├── _schema.md                # challenge config field reference
│   ├── level-00.yaml … level-08.yaml
├── backend/
│   ├── pyproject.toml  Dockerfile  alembic.ini
│   ├── alembic/                   # migrations
│   └── app/
│       ├── main.py                # FastAPI app factory
│       ├── api/                   # routers
│       │   ├── auth.py generate.py submit.py hints.py
│       │   └── scoreboard.py admin.py challenges.py
│       ├── core/                  # config.py security.py ratelimit.py logging.py
│       ├── engine/
│       │   ├── challenge_engine.py orchestrator.py template_renderer.py
│       │   ├── guardrails/        # base.py denylist.py classifier.py stateful.py output.py
│       │   └── tools/             # base.py admin_tools.py
│       ├── scoring/               # scoring_engine.py flag_validator.py hint_engine.py
│       ├── models/                # SQLAlchemy models
│       ├── schemas/               # Pydantic DTOs
│       ├── services/              # imagegen.py (runpod|mock) redis.py metadata.py ocr.py
│       └── tests/
├── frontend/
│   ├── package.json  vite.config.ts  Dockerfile  index.html
│   └── src/
│       ├── main.tsx App.tsx api/ store/
│       ├── views/   # Login ChallengeList ChallengePlay Scoreboard Admin
│       └── components/  # PromptForm AdvancedDrawer MetadataInspector HintDrawer FlagSubmit ConversationPane
├── infra/
│   ├── docker-compose.yml         # full local stack
│   ├── docker-compose.prod.yml    # event deploy overrides
│   ├── caddy/Caddyfile
│   ├── runpod/                    # handler.py Dockerfile.gpu requirements.txt
│   └── observability/             # prometheus.yml loki-config.yml grafana/dashboards/
└── scripts/                       # gen_access_codes.py seed_db.py loadtest.py
```

## 2. Database schema

See [`backend/alembic/versions/0001_initial.sql`](../backend/alembic/versions/0001_initial.sql) for
the runnable DDL. Summary:

```sql
CREATE TABLE teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  display_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'player'        -- player|instructor|admin
       CHECK (role IN ('player','instructor','admin')),
  access_code_hash TEXT UNIQUE NOT NULL,      -- single-use code, hashed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE challenges (
  id INT PRIMARY KEY,                         -- 0..8
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  owasp_tag TEXT NOT NULL,                     -- e.g. 'LLM07'
  base_points INT NOT NULL,
  sort_order INT NOT NULL,
  depends_on INT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  challenge_id INT NOT NULL REFERENCES challenges(id),
  seed BIGINT NOT NULL,
  rotating_state JSONB NOT NULL DEFAULT '{}', -- admin_workflow_id, planted memory, derived flag
  turn_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, challenge_id)
);

CREATE TABLE attempts (                        -- immutable audit of every generate + submit
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  challenge_id INT NOT NULL REFERENCES challenges(id),
  kind TEXT NOT NULL CHECK (kind IN ('generate','submit')),
  request JSONB NOT NULL,                       -- prompt + all fields (redacted of nothing - audit)
  response_ref TEXT,                            -- pointer to stored response/image
  verdict TEXT,                                 -- for submits: correct|incorrect|malformed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON attempts (user_id, challenge_id, created_at);

CREATE TABLE solves (
  user_id UUID NOT NULL REFERENCES users(id),
  challenge_id INT NOT NULL REFERENCES challenges(id),
  solved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  solve_rank INT NOT NULL,                       -- 1 = first blood
  points_awarded INT NOT NULL,
  PRIMARY KEY (user_id, challenge_id)
);

CREATE TABLE hints_taken (
  user_id UUID NOT NULL REFERENCES users(id),
  challenge_id INT NOT NULL REFERENCES challenges(id),
  tier INT NOT NULL,
  cost INT NOT NULL,
  taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, challenge_id, tier)
);

CREATE TABLE scores (                            -- materialized; also mirrored to Redis ZSET
  user_id UUID PRIMARY KEY REFERENCES users(id),
  total INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (                          -- append-only security/telemetry
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID,
  event TEXT NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'
);
```

## 3. API endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/redeem` | none | Redeem access code → JWT |
| GET  | `/api/challenges` | player | List challenges + lock/solve/points status |
| GET  | `/api/challenges/{id}` | player | Challenge detail (story, fields, hint availability) |
| POST | `/api/generate` | player | Core attack surface: generate image / model turn |
| POST | `/api/submit` | player | Submit a flag for a challenge |
| GET  | `/api/hints/{challenge_id}` | player | List hint tiers + costs + taken status |
| POST | `/api/hints/{challenge_id}/{tier}` | player | Take a hint (charges points) |
| GET  | `/api/scoreboard` | player | Snapshot leaderboard |
| WS   | `/ws/scoreboard` | player | Live leaderboard stream |
| POST | `/api/writeup` | player | Submit L8 disclosure writeup |
| GET  | `/api/admin/state` | admin | Live solve/stuck/RunPod state |
| POST | `/api/admin/imagegen-mode` | admin | Flip runpod↔mock failover |
| POST | `/api/admin/broadcast-hint` | admin | Free hint to all |
| POST | `/api/admin/reset-session` | admin | Reset a stuck attendee |
| POST | `/api/admin/lock-user` | admin | Kill-switch an account |

**`POST /api/generate` request:**
```json
{
  "challenge_id": 7,
  "prompt": "a serene mountain lake",
  "negative_prompt": "",
  "style_preset": "photoreal",
  "seed_caption": "",
  "image_b64": null,
  "session_id": "..."        // for multi-turn (L6/L8)
}
```
**Response:**
```json
{
  "image_url": "https://.../img/abc.png",
  "assistant_message": "Here is your image. ...",
  "session_id": "...",
  "turn": 3,
  "metadata_hint": "Provenance embedded in PNG."   // present only in vulnerable mode
}
```

## 4. Challenge configuration format

Full field reference in [`challenges/_schema.md`](../challenges/_schema.md). A challenge YAML declares
everything the engine needs to be vulnerable (or fixed):

```yaml
id: <int>
slug: <string>
name: <string>
owasp_tag: <LLM01..LLM10 | "chained">
difficulty: 1-5
base_points: <int>
depends_on: [<challenge ids>]
mode: vulnerable            # or 'fixed' for debrief
story: |
  ...
system_prompt: |            # may embed flag (L1)
  ...
template:
  mode: naive | structured  # naive = string interpolation (vulnerable)
  delimiters: { system: "<|system|>", user: "<|user|>" }
  body: |
    {system_prompt}
    {internal_directives}
    {user_prompt}
internal_directives: "..."  # server-only var (L5 target)
guardrails:
  pre:  [ { type: denylist, fields: [prompt] } ]   # L3: only 'prompt'
  post: [ ]                                          # weak/absent in vulnerable
tools: [ describe_admin_config, run_admin_workflow ] # L7/L8
ingest:
  ocr: true                 # L7 reads text from uploaded image
metadata:
  verbosity: verbose | minimal      # L4
seed_state:                 # per-session seeding
  rotating: [ admin_workflow_id ]
  planted_memory:           # L6
    - role: admin
      text: "deploy_secret = {flag}"
flag:
  type: static | derived
  value: "bsides{...}"      # static
  release_conditions:       # L8 precondition state machine
    - tool_invoked: run_admin_workflow
    - forged_role_seen: true
    - live_id_matches: true
hints:
  - { tier: 1, cost: 40,  text: "..." }
  - { tier: 2, cost: 80,  text: "..." }
  - { tier: 3, cost: 120, text: "..." }
mitigation: |
  ...
```

## 5. Example Docker Compose

See [`infra/docker-compose.yml`](../infra/docker-compose.yml) (runnable). It brings up postgres,
redis, backend, frontend, caddy, and the observability trio, with `mock` image gen by default.

## 6. Example challenge definition

See [`challenges/level-01.yaml`](../challenges/level-01.yaml) and
[`challenges/level-08.yaml`](../challenges/level-08.yaml) for the simplest and the most complex,
fully filled in.

## 7. Example flag validation logic

See [`backend/app/scoring/flag_validator.py`](../backend/app/scoring/flag_validator.py). Key points:
shape-check first, constant-time compare, per-session derivation via HMAC, rate-limited.

## 8. Example scoring logic

See [`backend/app/scoring/scoring_engine.py`](../backend/app/scoring/scoring_engine.py).
Idempotent first-solve scoring with rank-based decay + first-blood bonus, mirrored to Redis.
