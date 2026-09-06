# Naive RAG for admission-test MCQ generation

## Scope

- Exams: BUET and other engineering university admission tests
- Subjects: **Mathematics, Physics, Chemistry** (Bangla + LaTeX)
- KB: `documents/*.txt` (final format; legacy `*.json` still accepted)
  - File may contain **multiple JSON arrays** concatenated (page batches)
  - Each object: `question_number`, `question_type` (`MCQ`|`Written`), `subject`,
    `source_tag`, `question_text`, `options` (`{}` for Written, or a/b/c/...),
    `answer`, `solution`, `page_number`
- Output: `output_questions.json` (same MCQ schema as before, plus `subject`)

## What this does

1. **Ingest** all `documents/*.txt` (and legacy `*.json`) into a local vector KB (not Chemistry-only).
2. **Retrieve** top-k similar units for each skill/topic/Bloom/`subject` tuple.
   - Soft subject boost only (never hard-filters out other subjects).
3. **Generate** new MCQs via the Gemini API (`generate_question_gemini.py`) — see the
   repo root `HANDOFF.md` for the two-model generate/verify pipeline and key setup.

## Ontology input

Tuples and prereqs are read from `Backend/tree_data/ontology_source/` — the same
source the Backend compiles its skill DAG from, so generation and serving can never
drift onto different ontologies. See [TUPLE_FORMAT.md](TUPLE_FORMAT.md).

## Setup

From `data-gen/`:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

A Gemini API key (or several — see `keys/.gemini_keys`, one key per line, gitignored)
is required for generation. See `HANDOFF.md` for how keys/rate limits/models are used.

## Run

```powershell
# 1) Build / refresh KB whenever documents/*.txt changes
python -m rag.ingest

# Preferred: multilingual MiniLM embeddings (Bangla-capable).
# If HF download hangs, temporary offline fallback:
$env:RAG_FORCE_TFIDF = "1"
python -m rag.ingest

# 2) Smoke-test retrieval across subjects
python -m rag.retriever

# 3) Generate questions (Gemini, two-phase generate + batch-verify)
python generate_question_gemini.py --batch-size 200 --real

# 4) Check progress / ETA on a long run
python check_progress.py

# 5) Load them into Supabase for the engine to serve
python load_questions_to_supabase.py --input output_questions_gemini.json --dry-run
python load_questions_to_supabase.py --input output_questions_gemini.json --create-missing-skills
```

## Config knobs

See `config.py`:

- `EMBEDDING_MODEL_NAME` (default multilingual MiniLM)
- `TOP_K`, `SUBJECT_MATCH_BOOST`, `MCQ_MATCH_BOOST`
- `N_QUESTIONS`
- `EXPAND_ALL_BLOOM_LEVELS` — generate every skill at all six Bloom levels
  (430 tuples -> 2580). The engine asks for a question one Bloom level above the
  learner's current band, so partial coverage weakens the adaptive ladder.
  Disable for a quick run with `RAG_EXPAND_BLOOMS=0`.
