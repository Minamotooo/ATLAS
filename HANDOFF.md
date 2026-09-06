# ATLAS — Handoff

State of the branch as of the admission-test pivot. Read this first.

ATLAS is an adaptive tutoring platform: **Bayesian Knowledge Tracing over a
prerequisite skill DAG**, driving question selection for engineering university
admission tests (BUET/KUET/RUET/CUET). Bangla content with LaTeX math, three
subjects — Mathematics, Physics, Chemistry.

**The BCS arithmetic content is gone.** Ontology, question bank, prompts, the legacy
demo practice page — all removed. Anything BCS you remember is no longer here.

---

## 1. Where things stand

| Piece | State |
|---|---|
| Ontology (430 skills / 66 topics / 471 edges, admission-test pivot) | Done, compiled, synced to Supabase (old BCS ontology rows left intact, not deleted) |
| Catalog (3 courses / 20 sections) | Done |
| Backend adaptive engine | Done, boots clean, 18/18 smoke tests pass |
| Frontend | Builds clean |
| Supabase schema | `Backend/schema.sql`, ontology synced (insert-only — nothing old was deleted) |
| Question loader | `load_questions_to_supabase.py`, validated against a live DB, has run for real |
| **Question bank** | **In progress** — generation is a long-running batch job, see §2 |

Local Ollama generation was tried and abandoned (too slow on non-GPU hardware, and it
had a subtle JSON-corruption bug — see §5). Generation now runs against the **Gemini
API** instead, key-pooled across multiple free-tier keys for throughput.

---

## 2. Generating the question bank (Gemini pipeline)

### Setup

```bash
cd data-gen
python -m venv .venv && .venv/Scripts/activate       # Windows
pip install -r requirements.txt                      # torch + sentence-transformers, ~2.5 GB

# Build the retrieval KB from documents/ (4,474 items, one-off, a few minutes)
python -m rag.ingest
python -m rag.retriever          # sanity-check retrieval across subjects
```

Gemini keys: create `keys/.gemini_keys` at the repo root (gitignored), one API key per
line. The pipeline round-robins across all of them concurrently — each key/model pair
has its own independent rate limit, so more keys ~linearly raises throughput. Ask
whoever ran the last batch for the key list, or generate your own free-tier keys.

### Generate

```bash
cd data-gen
python generate_question_gemini.py --limit 6            # tiny pilot, cheap test model
python generate_question_gemini.py --sample-topics 5    # broader pilot, cheap test model
python generate_question_gemini.py --batch-size 200 --real   # real run, production model
python check_progress.py                                 # progress % and ETA at any time
```

- Reads tuples from `Backend/tree_data/ontology_source/` — the *same* source the
  Backend compiles its DAG from, so generation and serving cannot drift apart.
- **Bloom expansion is ON**: 430 skills × 6 Bloom levels = **2,580 tuples** total.
  `--batch-size N` processes the next N not-yet-done tuples each invocation, so a full
  run is just re-invoking with `--real` until `check_progress.py` shows 100%.
- Two-phase pipeline per tuple: generate (production model) → batch-verify (cheaper
  model does an independent on-topic check + a blind answer re-solve, batched several
  tuples per call to cut call count). Only questions that pass verification are written.
- Writes incrementally to `output_questions_gemini.json` / `gemini_progress.json` after
  each tuple finalizes — safe to kill and resume, nothing is corrupted mid-write, you
  just redo whatever was still in-flight.
- Rate-limited (429) keys back off adaptively and are retried, never permanently
  disabled; only an actual 401/403 (project blocked) retires a key for the run.

### Load into Supabase

```bash
cd data-gen
python load_questions_to_supabase.py --input output_questions_gemini.json --dry-run
python load_questions_to_supabase.py --input output_questions_gemini.json --create-missing-skills
```

The loader validates every constraint in `Backend/schema.sql` *before* writing,
normalizes Bloom casing to exactly what `server.py` filters on, resolves raw topic
labels to canonical codes, and dedups against existing rows (safe to re-run after each
new batch — already-loaded questions are skipped). Run `--dry-run` first, always — it
prints a full validation report. Needs `Backend/.env` with `SUPABASE_URL` and
`SUPABASE_SERVICE_KEY`.

---

## 3. Run the app

```bash
# Backend
cd Backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
# Backend/.env  ->  SUPABASE_URL=... / SUPABASE_SERVICE_KEY=...
uvicorn server:app --reload --port 8000

# Frontend
cd Frontend
npm install && npm run dev        # VITE_API_BASE_URL defaults to http://localhost:8000
```

Tests, no credentials required:

```bash
Backend/.venv/Scripts/python.exe Backend/smoke_test_engine.py     # 18 checks
```

Runs the diagnostic, mastery propagation and topic-practice spillover end-to-end
against an in-memory stand-in for Supabase.

---

## 4. Ontology — how to change it

Source of truth is `Backend/tree_data/ontology_source/`:

- `skill_ontology_dag.html` — **authoritative**. Embeds `NODES`, `EDGES`, `TOPIC_META`,
  `SUBJECT_ORDER`, `SUBJECT_TOPIC_ORDER`. The only source carrying topic→subject.
- `tuples.json`, `prereqs.json` — fallback, plus their own topic labels (which differ
  from the HTML's for the same code; the generator stamps *those* onto questions, so
  both are registered in `topic_resolution.json`).

Compile:

```bash
python Backend/tree_data/build_from_ontology.py --report-only          # inspect
python Backend/tree_data/build_from_ontology.py --out-dir Backend/tree_data --force
```

Editorial decisions live in **`Backend/tree_data/ontology_config.json`** — topic
aliases, display labels, course/section layout. Edit that, re-run, done. Everything
else is derived; don't hand-edit the generated files.

Two corrections the build applies, both load-bearing:

1. **Transitive reduction.** `prereqs.json` lists *ancestors*, not direct edges, and its
   `depth` field is uniformly `0`. Taken literally you get 44 shortcut edges. That is
   not cosmetic: the conjunctive transition gate reads `parent_ids`, so a shortcut lets
   a skill unlock while its true intermediate prerequisite is still unmastered.
2. **Topic canonicalization.** The ontology is three merged drafts — `MAT_`/`MATH_`,
   `CHE_`/`CHEM_`, plus pairs like `PHY_GRAV`/`PHY_GRAVITATION`. 49 codes collapse to
   canonical ones, 115 → 66 topics. Unmerged, the catalog lists "Complex Numbers" three
   times and topic practice covers a third of it.

---

## 5. Things you need to know

**Bloom coverage is the big open question.** The ontology assigns **one** Bloom level per
skill — 322 of 430 are `Apply`. But both the diagnostic and topic practice request a
question *one Bloom level above* the learner's current band. With a single-level bank
that ladder has nothing to climb and everything falls back to the nearby-Bloom search,
so mastery stops being meaningfully Bloom-conditioned. Hence `EXPAND_ALL_BLOOM_LEVELS`.
It is a 6× generation cost — worth confirming you agree before the full run.

**The Chemistry corpus had a corrupt record.** One `solution` field contained `\quad`
repeated 32,531 times (195 KB) and was left unterminated, which desynchronized the
parser and destroyed **334 sibling records**. Fixed two ways: the data is repaired
(`ChemBook2.txt`, original at `ChemBook2.txt.orig`, gitignored), and `salvage_objects()`
in `rag/ingest.py` now resynchronizes via `JSONDecoder.raw_decode` so a bad record costs
only itself. Corpus went 4,140 → **4,474 items** (Chemistry +25%). **If you add more
books, re-run `python -m rag.ingest`** and watch for `note: salvaged …` lines.

**Books tag Math as `"Higher Math"`,** not `"Mathematics"`. `SUBJECT_ALIASES` in
`rag/config.py` maps it, and subject boosting depends on that alias holding.

**Sessions are in-memory.** `DIAGNOSTIC_RUNS` / `TOPIC_PRACTICE_RUNS` /
`SECTION_PROGRESS` are module-level dicts. Single process only; a restart drops every
live session. Fine for demo, not for deployment.

**A bug worth knowing about, now fixed.** Tier 1 and Tier 2 of the diagnostic question
search filtered `questions.topic` by the catalog *display name*, but that column is
FK'd to `ontology_topics(topic_code)` and holds a code. Neither tier could ever match a
row — every question silently came from the no-topic fallback, and the DAG-nearby Tier 2
search never ran at all. There's a regression guard for it in `smoke_test_engine.py`.

**No `subject` column in the DB.** It is derived from the ontology
(`skill_subjects.json`) and plumbed through the API. If you want to filter questions by
subject in SQL, that needs a migration.

---

## 6. Layout

```
Backend/
  server.py                     FastAPI adaptive engine
  bkt.py bloom_taxonomy.py      BKT model + Bloom bands
  skill.py skill_tree.py        the DAG (cycle-checked, topologically sortable)
  mastery_updater.py            3-phase policy: Bloom-conditioned BKT, ancestor
                                pull-up, conjunctive transition gating
  diagnostic.py                 adaptive diagnostic session
  schema.sql                    live Supabase DDL (hand-maintained)
  smoke_test_engine.py          18-check end-to-end test, no credentials
  tree_data/
    ontology_source/            AUTHORITATIVE ontology input
    ontology_config.json        editorial layer — edit this
    build_from_ontology.py      compiler
    *.json                      generated; do not hand-edit
    sync_ontology_to_supabase.sql
data-gen/
  rag/                          ingest, embeddings, retriever, config
  question_gen_common.py        shared prompts, ontology loading, schema/LaTeX validation
  generate_question_gemini.py   Gemini generation (key-pooled, generate + batch-verify)
  check_progress.py             progress %/ETA for a running or paused generation batch
  load_questions_to_supabase.py question bank loader
keys/.gemini_keys                Gemini API keys, one per line (gitignored, not in repo)
documents/                      6 source books, 4,474 KB items
Frontend/                       React + Vite
BKT-DAG Policy For Skill Mastery.txt    the policy spec — describes real code
```

`BKT-DAG Policy For Skill Mastery.txt` documents actual implemented behaviour, not
intentions. Keep it in sync when you change policy.
