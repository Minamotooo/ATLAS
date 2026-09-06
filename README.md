# ATLAS

**A**daptive **T**utoring & **L**earning **A**ssessment **S**ystem — a Bayesian
Knowledge Tracing (BKT) tutor over a prerequisite skill DAG, built for engineering
university admission-test preparation (BUET / KUET / RUET / CUET style exams).
Content is Bangla with embedded LaTeX math, across three subjects: **Mathematics,
Physics, Chemistry**.

Given a learner's answers, the engine estimates per-skill mastery, propagates that
belief up a prerequisite graph, gates progression through the graph on
conjunctive prerequisite readiness, and selects each next question at the
learner's current Bloom's-Taxonomy zone of proximal development.

> **This file is the map of the repository.** For narrative history of *why*
> things are the way they are, see [`HANDOFF.md`](HANDOFF.md) and
> [`HANDOFF2.md`](HANDOFF2.md). For the exact, current runtime policy (thresholds,
> trigger rules, constants), see
> [`BKT-DAG Policy For Skill Mastery.txt`](BKT-DAG%20Policy%20For%20Skill%20Mastery.txt) —
> that document describes real implemented behavior, not aspiration.

---

## 1. Repository layout

```
ATLAS/
├── Backend/                   FastAPI adaptive engine (Python)
│   ├── server.py                 API routes, session state, question-selection policy
│   ├── bkt.py                    Stateless Bayesian Knowledge Tracing model
│   ├── bloom_taxonomy.py         Bloom levels ↔ 0–100 mastery bands
│   ├── mastery_updater.py        3-phase policy: Bloom-conditioned BKT, ancestor
│   │                              pull-up, conjunctive transition gating
│   ├── skill.py / skill_tree.py  Skill DAG (cycle-checked, topologically sortable)
│   ├── diagnostic.py             Adaptive diagnostic session (skill selection heuristic)
│   ├── schema.sql                Live Supabase DDL (hand-maintained, source of truth)
│   ├── smoke_test_engine.py      18-check end-to-end test, no DB credentials needed
│   ├── requirements.txt, Dockerfile, README.md
│   └── tree_data/
│       ├── ontology_source/         AUTHORITATIVE ontology input (HTML + JSON)
│       ├── ontology_config.json     Editorial layer — topic aliases, labels, course layout
│       ├── build_from_ontology.py   Compiles ontology_source/ + config → the *.json below
│       ├── *.json                   Generated — do not hand-edit
│       └── sync_ontology_to_supabase.sql / generate_ontology_sync_sql.js
│
├── Frontend/                  React 18 + Vite SPA
│   └── src/
│       ├── pages/                 One component per route (see §5)
│       ├── components/            Layout, Navbar, Footer, MathText (LaTeX renderer)
│       └── context/                AuthContext (localStorage session), LanguageContext (en/bn)
│
├── data-gen/                  Offline question-bank generation pipeline
│   ├── rag/                       Retrieval-augmented generation: ingest, embed, retrieve
│   ├── question_gen_common.py     Shared prompts, ontology loading, LaTeX/schema validation
│   ├── generate_question_gemini.py  Gemini-API generation (key-pooled, generate + batch-verify)
│   ├── check_progress.py          Progress %/ETA for a generation run
│   ├── load_questions_to_supabase.py  Validates + loads generated questions into the DB
│   └── requirements.txt
│
├── documents/                 6 source textbooks (Math/Physics/Chemistry) — RAG corpus
├── keys/.gemini_keys          Gemini API keys, one per line — gitignored, not in repo
├── HANDOFF.md, HANDOFF2.md    Dev handoff notes (chronological, read for history)
└── BKT-DAG Policy For Skill Mastery.txt   The policy spec — describes real code behavior
```

---

## 2. Architecture at a glance

```
 Frontend (React/Vite)  ──HTTP/JSON──▶  Backend (FastAPI, server.py)  ──▶  Supabase (Postgres)
                                              │
                                              ├─ SkillTree (skill.py, skill_tree.py)
                                              │     built once at boot from tree_data/*.json
                                              │
                                              ├─ DiagnosticSession (diagnostic.py)
                                              │     one per (user, section); in-memory
                                              │
                                              ├─ MasteryUpdater (mastery_updater.py)
                                              │     BKTModel (bkt.py) + Bloom bands
                                              │     (bloom_taxonomy.py) + ancestor pull-up
                                              │     + conjunctive transition gating
                                              │
                                              └─ TOPIC_PRACTICE_RUNS / SECTION_PROGRESS
                                                    module-level dicts (in-memory sessions)
```

Question **content** (stems, options, explanations, missing-prerequisite tags) lives in
Supabase, generated offline by the `data-gen/` pipeline. Question **selection policy**
(which skill, which Bloom level, which DAG-nearby fallback) lives entirely in the
Backend and is independent of how the bank was generated.

---

## 3. Core concepts

### 3.1 Bayesian Knowledge Tracing ([`bkt.py`](Backend/bkt.py))

Each skill's mastery is a latent probability `P(learned)` in `[0, 1]`, persisted as a
percentage `[0, 100]` (`mastery = 100 × P(learned)`). Four parameters govern the
model per answer: `P(L₀)` prior, `P(T)` learning rate, `P(S)` slip, `P(G)` guess.
The model is stateless — it takes a current probability and an observation
(correct/incorrect) and returns the updated probability; all state lives in the DB.

### 3.2 Bloom's Taxonomy bands ([`bloom_taxonomy.py`](Backend/bloom_taxonomy.py))

The 0–100 mastery scale is split into six equal ~16.67-point bands, one per Bloom
level (Remember → Understand → Apply → Analyze → Evaluate → Create). Guess/slip
probabilities are **Bloom-conditioned** — higher cognitive levels are harder to guess
and easier to slip on:

| Bloom level | P(guess) | P(slip) |
|---|---|---|
| Remember | 0.30 | 0.05 |
| Understand | 0.25 | 0.08 |
| Apply | 0.18 | 0.12 |
| Analyze | 0.12 | 0.18 |
| Evaluate | 0.08 | 0.22 |
| Create | 0.05 | 0.25 |

### 3.3 Skill DAG ([`skill.py`](Backend/skill.py), [`skill_tree.py`](Backend/skill_tree.py))

Skills form a directed acyclic graph of prerequisites (cycle-checked, topologically
sortable). Compiled from `Backend/tree_data/ontology_source/` — currently **430
skills, 66 canonical topics, 471 prerequisite edges**, max depth 7.

### 3.4 Mastery propagation & gating ([`mastery_updater.py`](Backend/mastery_updater.py))

Three-phase policy applied on every answer:
1. **Bloom-conditioned BKT update** on the answered skill.
2. **Ancestor pull-up** — a correct answer on skill `C` raises every ancestor to
   `max(current, P(C))`; incorrect answers never push ancestors down.
3. **Conjunctive transition gating** — a skill can only transition (learning-rate
   `P(T)`) if **all** of its direct parents are at ≥95% mastery; otherwise it uses a
   near-zero locked transition rate. This is the DAG "gate": you cannot race ahead
   of an unmastered prerequisite chain.

### 3.5 Diagnostic → Topic practice → Spillover

- **Section diagnostic** (`/diagnostic/*`): a fixed-length (default 30, floor 5,
  capped at section skill count), one-skill-once adaptive probe. Picks skills by a
  balanced-volume heuristic over untested ancestors/descendants, then a question one
  Bloom level above the learner's current estimate. Must be completed before mastery
  views or topic practice unlock.
- **Topic practice** (`/topic-practice/*`): after the diagnostic, practice per topic
  starting from the learner's weakest-but-started skill, traversing the topic's
  reduced DAG until every skill in it hits 95% mastery.
- **Prerequisite spillover**: if a learner keeps missing questions that point to the
  same weak prerequisite (rule A: ≥3 of last 5 wrong attempts implicate it; rule B:
  <40% accuracy over last 8 attempts *and* a candidate prerequisite is <60%
  mastered), the engine injects 2 questions on that prerequisite before resuming
  topic traversal.

Full constants, trigger thresholds, and edge cases:
[`BKT-DAG Policy For Skill Mastery.txt`](BKT-DAG%20Policy%20For%20Skill%20Mastery.txt).

**Sessions are in-memory** (`DIAGNOSTIC_RUNS`, `TOPIC_PRACTICE_RUNS`,
`SECTION_PROGRESS` are module-level dicts) — single process only, a backend restart
drops every live session. Fine for a demo, not for production deployment.

---

## 4. Data model (Supabase / Postgres)

Defined in [`Backend/schema.sql`](Backend/schema.sql) (hand-maintained, verbatim from
the live dashboard — the actual source of truth if this file and the DB ever
disagree, fix the file).

| Table | Purpose |
|---|---|
| `users` | Username only, no password (see §8 limitations) |
| `user_skill` | Per-user mastery level (0–100) per skill |
| `skills` | Skill catalog (id, description) |
| `questions` | Question stem, Bloom level, topic code (FK → `ontology_topics`, **not** a display label) |
| `question_options` | A–D options per question, `is_correct`, per-option explanation |
| `option_missing_prerequisites` | Which prerequisite skill a wrong option's mistake implicates — feeds the spillover policy |
| `ontology_topics` | Topic code ↔ display label |
| `ontology_skill_topics` | Skill ↔ topic membership |
| `ontology_skill_edges` | Prerequisite edges (source → target) |

Notes worth remembering (also in the schema file's header): no unique constraint on
`questions` beyond its surrogate id, so loaders must dedup themselves; no `subject`
column anywhere (subject is derived from the ontology and plumbed through the API,
not queryable in SQL directly).

---

## 5. API reference (`Backend/server.py`)

| Method & path | Purpose |
|---|---|
| `GET /catalog` | Full course/section/topic catalog |
| `GET /users/{user_name}/` | Look up a user by name |
| `POST /users/` | Create a user (username only) |
| `GET /users/{user_id}/sections/{section_id}/state` | Diagnostic/lock state for a section |
| `GET /users/{user_id}/sections/{section_id}/mastery` | Mastery map + table for visualization |
| `POST /users/{user_id}/sections/{section_id}/diagnostic/retake` | Reset mastery + sessions for a section |
| `POST /diagnostic/start` | Begin a section diagnostic session |
| `GET /diagnostic/{session_id}/status` | Diagnostic session status |
| `GET /diagnostic/{session_id}/next` | Fetch the next diagnostic question |
| `POST /diagnostic/{session_id}/answer` | Submit an answer, trigger mastery update |
| `POST /topic-practice/start` | Begin topic practice for a topic |
| `GET /topic-practice/{session_id}/status` | Topic practice session status |
| `GET /topic-practice/{session_id}/next` | Fetch the next topic-practice question |
| `POST /topic-practice/{session_id}/answer` | Submit an answer, may trigger spillover |

CORS is wide open (`allow_origins=["*"]`) — fine for a local/demo deployment, not for
production.

---

## 6. Frontend routes (`Frontend/src/App.jsx`)

| Route | Page |
|---|---|
| `/` | `LandingPage` |
| `/login`, `/signup` | `LoginPage`, `SignupPage` (username-only, no password) |
| `/courses` | `CoursesPage` — course list |
| `/courses/:courseId` | `LessonsPage` — sections within a course |
| `/courses/:courseId/sections/:sectionId` | `SectionPage` — diagnostic flow |
| `/courses/:courseId/sections/:sectionId/mastery` | `SectionMasteryPage` — mastery map/table |
| `/courses/:courseId/sections/:sectionId/topics/:topicCode/practice` | `TopicPracticePage` |

Bilingual (English/Bangla) via `LanguageContext`. Session is a plain `user_id`/`user_name`
pair kept in `localStorage` via `AuthContext` — there is no token, password, or
server-side session; see §8.

Question stems, options, and explanations mix Bangla text with inline (`$...$`) or
display (`$$...$$`) LaTeX. These are rendered client-side by
[`MathText.jsx`](Frontend/src/components/MathText.jsx) via KaTeX — it also normalizes
literal `\n` sequences (some generated content stores them as two literal characters
rather than a real line break) into actual line breaks.

---

## 7. Question bank generation (`data-gen/`)

Offline pipeline, independent of the running app:

1. **Ingest** (`rag/ingest.py`): parses `documents/*.txt` (6 source textbooks) into a
   local retrieval knowledge base (`rag/kb/items.jsonl`, gitignored, rebuild with
   `python -m rag.ingest`).
2. **Generate** (`generate_question_gemini.py`): for each (skill, Bloom-level) tuple
   — 430 skills × 6 Bloom levels = 2,580 tuples — retrieves relevant KB material,
   prompts the Gemini API for MCQs grounded in it.
3. **Verify**: a second, cheaper Gemini model independently checks each question is
   on-topic and blind-re-solves it (no access to the marked answer) to confirm the
   correct option. Only questions passing both checks are kept.
4. **Load** (`load_questions_to_supabase.py`): validates every DB constraint,
   normalizes Bloom casing, resolves topic labels to canonical codes, dedups against
   what's already loaded, and writes to Supabase.

Needs `keys/.gemini_keys` (one API key per line, gitignored) and
`Backend/.env` (`SUPABASE_URL` / `SUPABASE_SERVICE_KEY`). Full walkthrough, including
why the original local-Ollama approach was abandoned, in
[`HANDOFF2.md`](HANDOFF2.md).

---

## 8. Running it locally

```bash
# Backend
cd Backend
python -m venv .venv && .venv/Scripts/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# create Backend/.env:
#   SUPABASE_URL=...
#   SUPABASE_SERVICE_KEY=...
uvicorn server:app --reload --port 8000

# Frontend (separate terminal)
cd Frontend
npm install
npm run dev        # defaults to http://localhost:8000 for the API (VITE_API_BASE_URL)
```

No-credentials sanity check (18 checks against an in-memory Supabase stand-in):
```bash
Backend/.venv/Scripts/python.exe Backend/smoke_test_engine.py
```

To change the ontology (topic aliases, display labels, course/section layout), edit
`Backend/tree_data/ontology_config.json`, then:
```bash
python Backend/tree_data/build_from_ontology.py --out-dir Backend/tree_data --force
node Backend/tree_data/generate_ontology_sync_sql.js
# run the generated tree_data/sync_ontology_to_supabase.sql in Supabase
```

---

## 9. Known limitations & open items

- **`Backend/Dockerfile`'s `CMD` is stale** — it runs `uvicorn main:app`, but the
  actual entrypoint module is `server.py` (`uvicorn server:app`). There is no
  `main.py`; the container as written will not start. Needs a one-line fix before
  Docker deployment is attempted.
- **No real authentication.** Login is username-only (no password), and the
  frontend session is just a `user_id`/`user_name` pair in `localStorage` with no
  server-side token. Fine for a classroom demo, not for anything handling real
  accounts.
- **Sessions are in-memory** on the backend (diagnostic runs, topic-practice runs,
  section progress). A backend restart silently drops every active session.
- **Bloom coverage is thin.** The source ontology assigns one Bloom level per skill
  (mostly *Apply*), but both the diagnostic and topic practice request a question one
  Bloom level above the learner's current band. Until the 6-level-expanded question
  bank (`EXPAND_ALL_BLOOM_LEVELS` in `data-gen`) is fully generated, most of that
  ladder falls back to nearby-Bloom search rather than a real climb.
- **Question bank is a work in progress** — see `HANDOFF2.md` §5 for the live count;
  as of that writing only ~18% of the (skill × Bloom-level) tuple space had been
  generated and loaded, so coverage varies a lot by topic.
- **No `subject` column in the DB** — subject is derived from the ontology at read
  time. Filtering questions by subject in raw SQL needs a migration first.
- **CORS is wide open** (`allow_origins=["*"]`) — acceptable for local/demo use, not
  for a public deployment.

---

## 10. Where to look next

- Changed something in the ontology and confused about topic codes vs. labels? →
  `Backend/tree_data/ontology_config.json` header comment, and §4 of `HANDOFF.md`.
- Changed the mastery/gating policy and need the exact constants? →
  `BKT-DAG Policy For Skill Mastery.txt`.
- Need to know why a design decision was made (Ollama → Gemini, JSON-escape bugs,
  corpus corruption)? → `HANDOFF2.md`.
- Everything else historical (BCS-era removal, the original admission-test pivot)? →
  `HANDOFF.md`.
