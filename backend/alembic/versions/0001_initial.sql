-- Baseline schema for the CTF platform (Phase 6 §2). Runnable as a plain SQL migration; the Alembic
-- version wraps this DDL. Postgres 16. Requires pgcrypto for gen_random_uuid().
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE teams (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id          UUID REFERENCES teams(id),
  display_name     TEXT NOT NULL,
  role             TEXT NOT NULL DEFAULT 'player'
                   CHECK (role IN ('player','instructor','admin')),
  access_code_hash TEXT UNIQUE NOT NULL,        -- single-use access code, hashed
  locked           BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE challenges (
  id          INT PRIMARY KEY,                  -- 0..8
  slug        TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  owasp_tag   TEXT NOT NULL,
  base_points INT NOT NULL,
  sort_order  INT NOT NULL,
  depends_on  INT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE sessions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id),
  challenge_id   INT  NOT NULL REFERENCES challenges(id),
  seed           BIGINT NOT NULL,
  rotating_state JSONB NOT NULL DEFAULT '{}',   -- admin_workflow_id, planted memory, derived flag salt
  turn_count     INT NOT NULL DEFAULT 0,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, challenge_id)
);

CREATE TABLE attempts (                          -- immutable audit of every generate + submit
  id           BIGSERIAL PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  challenge_id INT  NOT NULL REFERENCES challenges(id),
  kind         TEXT NOT NULL CHECK (kind IN ('generate','submit')),
  request      JSONB NOT NULL,                   -- prompt + all fields
  response_ref TEXT,
  verdict      TEXT,                             -- submits: correct|incorrect|malformed
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX attempts_user_chal_idx ON attempts (user_id, challenge_id, created_at);

CREATE TABLE solves (
  user_id        UUID NOT NULL REFERENCES users(id),
  challenge_id   INT  NOT NULL REFERENCES challenges(id),
  solved_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  solve_rank     INT NOT NULL,                   -- 1 = first blood
  points_awarded INT NOT NULL,
  PRIMARY KEY (user_id, challenge_id)
);
CREATE INDEX solves_chal_rank_idx ON solves (challenge_id, solve_rank);

CREATE TABLE hints_taken (
  user_id      UUID NOT NULL REFERENCES users(id),
  challenge_id INT  NOT NULL REFERENCES challenges(id),
  tier         INT NOT NULL,
  cost         INT NOT NULL,
  taken_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, challenge_id, tier)
);

CREATE TABLE scores (                            -- materialized; mirrored to a Redis ZSET
  user_id    UUID PRIMARY KEY REFERENCES users(id),
  total      INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE writeups (                          -- L8 disclosure submissions
  user_id      UUID PRIMARY KEY REFERENCES users(id),
  body         TEXT NOT NULL,
  bonus_points INT,                              -- judged 0..200
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (                          -- append-only security/telemetry
  id     BIGSERIAL PRIMARY KEY,
  ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID,
  event  TEXT NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}'
);
