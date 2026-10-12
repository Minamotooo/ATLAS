# CLAUDE.md

Instructions for Claude Code (or any agent) asked to run, validate or evaluate this
repository. Read this before running anything. [README.md](README.md) is the short
human-facing overview; this file has the operational detail. Architecture, the full
API reference and the database schema are in [ARCHITECTURE.md](ARCHITECTURE.md).

## What this project is

ATLAS is the CSE 450 Capstone project of Group 07 (Dept. of CSE, BUET), supervised by
Dr. Md. Shariful Islam Bhuyan. It is an adaptive tutor for engineering-admission-test
Physics, Chemistry and Mathematics. It runs Bayesian Knowledge Tracing (BKT) over a
prerequisite skill graph (DAG), using Bloom-level-conditioned guess and slip rates,
ancestor pull-up, conjunctive prerequisite gating and prerequisite "spillover".

It has three parts:

| Part | Stack | Where it runs in production |
|---|---|---|
| `Backend/` | Python, FastAPI, uvicorn | Render (Docker, free tier): https://atlas-api-5wjp.onrender.com |
| `Frontend/` | React 18, Vite, Tailwind, KaTeX, Cytoscape | Vercel: https://atlas-indol-one.vercel.app |
| Database | Supabase (Postgres) | Supabase cloud project (shared by local and deployed) |

Deliverables in this repository:

- **Final report:** [Final_report/Group07_ATLAS.pdf](Final_report/Group07_ATLAS.pdf),
  the submitted version. The LaTeX source is next to it (`template.tex`, `chapters/`,
  `figures/`; build with `latexmk -pdf template.tex`).
- **Slides:** [Presentation/](Presentation/).
- **Source:** everything else. The prompts that built the content are in
  [Prompts/](Prompts/).

## Fastest way to validate (no credentials needed)

Run these from the repository root. All of them work without `Backend/.env`.

```bash
# 1. Engine + auth test harness (in-memory Supabase stand-in, no network)
cd Backend
python -m venv .venv
.venv/Scripts/activate            # Windows bash; PowerShell: .venv\Scripts\Activate.ps1; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python smoke_test_engine.py       # expect: === 54 passed, 0 failed ===
cd ..

# 2. Ontology structural validator (acyclic, no orphans, every topic populated)
Backend/.venv/Scripts/python Ontology/full_corpus_rebuild/_validate_ontology.py
#    expect: "ontology: 1688 skills, 1743 edges, 183 topics" and
#    PASS  (0 error-level, 4 warn-level). The warnings are review-only listings
#    (Bloom inversions, cross-subject edges such as Physics kinematics -> Maths
#    plane motion), not defects.

# 3. Frontend production build
cd Frontend && npm install && npm run build   # expect: "built in ..."; the >500 kB chunk warning is harmless
```

What the smoke test covers: sections 1–7 (30 checks) run the ontology load, the
topic-code question search, the full diagnostic, ancestor pull-up, the mastery view,
mixed answers, and topic practice with spillover. These are the engine harness
described in the report's evaluation chapter, which quotes 29 checks; the harness had
30 by the final commit. Section 8 (24 checks) was added after the report, when
sign-in moved to passwords for the public deployment. It covers signup and login,
scrypt hashing, token expiry and forgery, per-learner ownership, admin gating and
login throttling, all over HTTP via FastAPI's TestClient.

If this passes but the live server fails, the cause is almost certainly the
credentials or the database (see below), not the code.

## Checking the deployed system

The deployment is live and uses the same code as this repository.

```bash
curl https://atlas-api-5wjp.onrender.com/catalog        # JSON: {"courses": [...]}, 3 courses, 51 sections
curl https://atlas-api-5wjp.onrender.com/stats/public   # live figures, see below
```

As of 2026-10-12, `/stats/public` returns 3 subjects, 51 sections, 183 topics, 1,688
skills (Chemistry 886, Mathematics 446, Physics 356), 1,683 prerequisite edges and
12,223 questions.

- **Cold start:** the Render free tier sleeps after about 15 idle minutes. The first
  request can take about 60 s or time out once; retry before concluding it is down.
- **Supabase pause:** free-tier Supabase projects pause after a long period of
  inactivity. Symptoms are `getaddrinfo failed` / `Name or service not known` in the
  API logs, or 5xx errors from routes that touch the database. `/catalog` is served
  from files baked into the image, so it can still respond while the DB is paused. Only
  the team can un-pause the project, from the Supabase dashboard.
- In the browser: open https://atlas-indol-one.vercel.app, sign up with any new
  username and a password of 8+ characters, open a course, pick a section, and take the
  diagnostic. When it finishes, the section's mastery map (`.../mastery`) and topic
  practice unlock. `/mastery` shows the learner-wide map.

### End-to-end API walkthrough (optional, creates one real account)

Works against the deployed API or a local one (`BASE=http://localhost:8000`). Note
that this writes a real user and their mastery rows to the shared database.

```bash
BASE=https://atlas-api-5wjp.onrender.com
NAME="eval_$(date +%s)"
RESP=$(curl -s -X POST $BASE/auth/signup -H 'Content-Type: application/json' \
  -d "{\"user_name\":\"$NAME\",\"password\":\"evaluate-123\"}")      # -> {"token":..., "user":{"user_id":...}}
TOKEN=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
UID_=$(echo "$RESP"  | python -c "import sys,json;print(json.load(sys.stdin)['user']['user_id'])")
AUTH="Authorization: Bearer $TOKEN"

# Start a section diagnostic (section ids come from /catalog, e.g. mat1_ch01_matrix)
START=$(curl -s -X POST $BASE/diagnostic/start -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"$UID_\",\"section_id\":\"mat1_ch01_matrix\"}")   # -> session_id, total_questions, question{options[{label,text}]}
SID=$(echo "$START" | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")

curl -s -X POST $BASE/diagnostic/$SID/answer -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"selected_option_label":"A"}'                                  # mastery update + next state
curl -s $BASE/diagnostic/$SID/next   -H "$AUTH"                       # next question
curl -s $BASE/users/$UID_/sections/mat1_ch01_matrix/mastery -H "$AUTH"  # mastery map (full after the diagnostic completes)
```

Every route except `/catalog`, `/stats/public`, `/auth/signup` and `/auth/login`
needs the bearer token. The complete route table is in ARCHITECTURE.md §5.

## Running locally

### Step 1: check for `Backend/.env` first

```bash
ls Backend/.env   # PowerShell: Test-Path Backend/.env
```

This file is **not** in the repository. It is gitignored because it holds the
Supabase service-role key, which has full database access. The team shares it
privately (email or LMS) with anyone evaluating the project. Place it at
`Backend/.env`. [Backend/.env.example](Backend/.env.example) is the template.

| Variable | Required | Default if unset | Purpose |
|---|---|---|---|
| `SUPABASE_URL` | **yes** | none, crash | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_KEY` | **yes** | none, crash | Service-role key (Supabase → Project Settings → API) |
| `AUTH_SECRET` | recommended | random per process | Signs HS256 login tokens (7-day expiry). If unset, every restart, including each `--reload`, signs everyone out. Any long random string works: `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ADMIN_USERNAMES` | no | empty, no admins | Comma-separated names allowed into `/admin/*` |
| `DEMO_SHOW_ANSWERS` | no | `0` | `1` sends the correct option to the browser (demo aid) |
| `CORS_ORIGINS` | no | `*` | Comma-separated allowed origins |
| `NEXT_QUESTION_DEBUG_LOGS` | no | `true` | Verbose question-selection logs |
| `DIAGNOSTIC_QUESTION_COUNT` | no | `30` | Target diagnostic length (capped at the section's skill count) |

The frontend has one optional variable, `VITE_API_BASE_URL` (default
`http://localhost:8000`). It is read at build time, so set it in `Frontend/.env.local`
or the shell before running `npm run dev` / `npm run build`. No frontend `.env` is
needed for local use.

**If `Backend/.env` is missing:** do not invent, guess or stub values into a real
`.env`. `Backend/server.py` reads `os.environ["SUPABASE_URL"]` at import time and
raises `KeyError` with no fallback. That crash is expected, not a bug to patch.
Validate with the no-credential steps above and the deployed system instead, and tell
the user the local server can't start without the real file.

**The supplied `.env` points at the team's populated database.** An empty Supabase
project will not work as-is. It would need `Backend/schema.sql`, the ontology sync
(`Backend/tree_data/generate_ontology_sync_sql.js`), and a question-bank load
(`data-gen/load_questions_to_supabase.py`, whose generated input files are gitignored).
Use the provided credentials rather than rebuilding the database.

### Step 2: start the backend

```bash
cd Backend
python -m venv .venv                       # Python 3.11+ (production image uses 3.13)
.venv/Scripts/activate                     # see activation variants above
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8000
```

`uvicorn` blocks, so run it in the background or in a separate terminal. A
`WARN: AUTH_SECRET is not set` line is fine locally. Startup also loads the ontology
JSON from `Ontology/full_corpus_rebuild/` (for the admin ontology page), so run it
from inside a full checkout.

Verify it came up:

```bash
curl http://localhost:8000/catalog    # JSON with a "courses" array
```

If the connection is refused, read the process output. A `KeyError` means the `.env`
is missing or malformed. `Address already in use` means port 8000 is taken: use
`--port 8001` and set `VITE_API_BASE_URL=http://localhost:8001` for the frontend.
DNS errors mean the Supabase project is paused (see above).

### Step 3: start the frontend (after the backend responds)

```bash
cd Frontend
npm install          # Node 18+
npm run dev          # prints http://localhost:5173
```

### Admin pages (optional)

`/admin/stats` (cohort mastery statistics + CSV/JSON export) and `/admin/ontology`
(ontology browser/editor) need an account whose name is in `ADMIN_USERNAMES`. Admin
names cannot self-register. Create one with:

```bash
cd Backend && python set_password.py <name> --create    # prompts for the password
```

This writes to the shared database, so only do it if the user asks.

## Key numbers, and why some differ

| Figure | Value | Note |
|---|---|---|
| Skills | 1,688 | `Ontology/full_corpus_rebuild/` (source) and `Backend/tree_data/*.json` (compiled, served) |
| Prerequisite edges in the source ontology | 1,743 | the figure the report quotes |
| Prerequisite edges served | 1,683 | the same graph after transitive reduction (60 redundant edges dropped) |
| Topics / sections / subjects | 183 / 51 / 3 | |
| Verified questions | 12,223 | covering 89% of the 10,128 (skill, Bloom level) specs (report) |
| DAG depth | 9 | |

Reproduce the compile figures with
`python Backend/tree_data/build_from_ontology.py --report-only --source-dir Ontology/full_corpus_rebuild`.
Without `--source-dir`, the script reads the legacy 430-skill
`Backend/tree_data/ontology_source/`, which is kept only as a reference. Its numbers
(430 skills, 471 edges) are not what the app serves.

## Things that look wrong but are intentional (don't "fix" these)

- **Sessions are in-memory** (diagnostic runs, topic-practice runs, section
  progress). A backend restart or a Render sleep drops active sessions. Mastery already
  written to Supabase survives. This is a documented limitation.
- **Accounts with a NULL `password_hash` can't log in** (`403`). They predate
  passwords. An admin fixes them with `Backend/set_password.py`.
- **Admin names can't self-register.** `/auth/signup` refuses names in
  `ADMIN_USERNAMES`.
- **CORS defaults to `*`.** Auth uses bearer tokens, not cookies.
- **`questions.topic` stores a topic CODE** (e.g. `MAT_MATRIX`), not a display label.
- **Not every (skill × Bloom level) pair has questions** (89% coverage). When the exact
  level is missing, the engine falls back to a nearby Bloom level or a nearby skill.
  That is designed behaviour, not an engine bug.
- **Admin ontology edits on Render don't persist.** The container disk resets on
  restart.
- **`npm run build` warns about chunks over 500 kB** (three.js / Cytoscape). Harmless.

## Git conduct

Don't commit, push, force-push or otherwise alter git history or remote state unless
the user explicitly asks in that specific message. Read-only commands (`git log`,
`git diff`, `git status`) are always fine. Never commit `Backend/.env` or
`keys/.gemini_keys`.

## Documentation map

- [README.md](README.md): overview, live links, quick start.
- [ARCHITECTURE.md](ARCHITECTURE.md): repository layout, core algorithms, DB schema,
  full API reference, frontend routes, the `data-gen` pipeline, known limitations.
- [DEPLOY.md](DEPLOY.md): how the Vercel + Render + Supabase deployment was set up,
  with the configuration reference and free-tier caveats.
- [BKT-DAG Policy For Skill Mastery.txt](BKT-DAG%20Policy%20For%20Skill%20Mastery.txt):
  exact mastery and gating constants and trigger rules, matching the code.
- [Backend/README.md](Backend/README.md): backend commands (accounts, ontology
  compile, tests).
- [Prompts/](Prompts/): every LLM prompt that shaped the content, in pipeline order
  (syllabus → taxonomy → ontology extraction → editorial QA → question generation →
  verification). Prompts 05–07 copy live strings in `data-gen/`, and the code is the
  source of truth.
- [data-gen/](data-gen/): offline question generation (RAG over `documents/`, Gemini
  generate-then-verify, Supabase loader). It needs `keys/.gemini_keys` (gitignored, one
  API key per line) and is not needed to run or evaluate the app.
- [Ontology/full_corpus_rebuild/STATUS.md](Ontology/full_corpus_rebuild/STATUS.md):
  final state of the ontology. Run `_validate_ontology.py` after any change to it.
  [Ontology/viz/README.md](Ontology/viz/README.md) covers the generated HTML viewers.
- [HANDOFF.md](HANDOFF.md) → [HANDOFF5.md](HANDOFF5.md): chronological development
  history and the reasons behind major decisions (ontology rebuild, Ollama → Gemini,
  and so on). Their figures are historical. Where they disagree with this file or
  the report, this file and the report are current.
