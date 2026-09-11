# CLAUDE.md

Instructions for Claude Code (or any agent) operating in this repository. Read this
before running anything. For deep architecture/API/data-model detail, see
[README.md](README.md) — this file only covers what's needed to get the app running.

## What this project is

ATLAS: a FastAPI backend (Bayesian Knowledge Tracing over a skill prerequisite DAG)
plus a React/Vite frontend, backed by Supabase (Postgres). Two independent halves —
`Backend/` and `Frontend/` — started separately, talking over HTTP on `localhost`.

## Step 1 — check whether `Backend/.env` exists before doing anything else

```bash
ls Backend/.env   # or: Test-Path Backend/.env  in PowerShell
```

This file is intentionally **not** in the repo (gitignored — it holds a Supabase
service key, a secret with full database access). Whoever gave you this repo should
have handed you this file separately (email, LMS attachment, etc.), to be placed at
`Backend/.env` with this exact shape:

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service role key>
```

**If it's missing:** do not invent, guess, or stub these values into a real `.env` —
`Backend/server.py` reads them with `os.environ["SUPABASE_URL"]` at import time and
will raise `KeyError` immediately with no fallback if they're absent. That crash is
expected behavior, not a bug to patch. In that case, skip to **Step 4 (no-credential
verification)** below and tell the user the live app can't start until they provide
`Backend/.env` — don't spend time trying to work around it.

## Step 2 — start the backend

```bash
cd Backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   (PowerShell)  or  .venv/Scripts/activate  (bash)
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

`uvicorn` blocks the terminal — run it as a background process (or in a separate
terminal/session) so you can keep issuing commands afterward.

Verify it actually came up before moving on:

```bash
curl http://localhost:8000/catalog
```

Expect JSON with a `courses` array. A connection error means the process didn't
start — check its output first for a `KeyError` (missing/malformed `.env`, see Step
1) before assuming anything else is wrong. Port 8000 already in use is the other
common cause; free it or pass `--port` with a different number (and adjust the
frontend's `VITE_API_BASE_URL` to match if you do).

## Step 3 — start the frontend (separate terminal, after the backend responds)

```bash
cd Frontend
npm install
npm run dev
```

No `.env` needed — it defaults to `http://localhost:8000` for the API
(`VITE_API_BASE_URL`). Vite prints the local URL to open (usually
`http://localhost:5173`).

## Step 4 — no-credential verification (works with or without `Backend/.env`)

```bash
cd Backend
python -m venv .venv && pip install -r requirements.txt   # if not already done
python smoke_test_engine.py
```

Expect `18 passed, 0 failed`. This runs the full diagnostic → mastery-update →
topic-practice → spillover flow against an in-memory Supabase stand-in — use it to
confirm the engine logic itself is sound even when there's no live database
connection. If this fails, that's a real regression worth investigating; if only the
live server (Step 2) fails while this passes, the problem is almost certainly
missing/invalid Supabase credentials, not the code.

## Things that look wrong but are intentional — don't "fix" these

- **Sessions are in-memory** (diagnostic runs, topic-practice runs, section
  progress). Restarting the backend silently drops every active session. Expected
  for the project's current stage, not a bug.
- **Login is username-only, no password.** `AuthContext` just stores
  `user_id`/`user_name` in `localStorage`. Not a security bug to patch here.
- **CORS is wide open** (`allow_origins=["*"]`). Intentional for local/demo use.
- **`questions.topic` in the DB stores a topic CODE** (e.g. `MAT_MATRIX`), not a
  display label — expected, don't "fix" data that looks uses codes instead of
  readable names.
- **The question bank may be incomplete.** Coverage of the full (skill × Bloom
  level) space can be partial depending on how much of the generation pipeline in
  `data-gen/` has been run — see `HANDOFF2.md` for the state as of the last update.
  Thin coverage for a given topic is a data-completeness issue, not an engine bug.

## Git conduct

Don't commit, push, force-push, or otherwise alter git history/remote state unless
the user explicitly asks in that specific message. Read-only exploration
(`git log`, `git diff`, `git status`) is always fine.

## Full documentation map

- [README.md](README.md) — architecture, full API reference, DB schema, frontend
  routes, the `data-gen` question-generation pipeline, known limitations.
- [HANDOFF.md](HANDOFF.md), [HANDOFF2.md](HANDOFF2.md) — chronological dev history
  and rationale for major decisions.
- [BKT-DAG Policy For Skill Mastery.txt](BKT-DAG%20Policy%20For%20Skill%20Mastery.txt)
  — exact current mastery/gating policy constants and trigger rules.
