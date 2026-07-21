# Naive RAG for BUET / admission MCQ generation

## Scope

- Exams: BUET and other engineering university admission tests
- Subjects: **Mathematics, Physics, Chemistry** (Bangla + LaTeX)
- KB: `bktback/documents/*.txt` (final format; legacy `*.json` still accepted)
  - File may contain **multiple JSON arrays** concatenated (page batches)
  - Each object: `question_number`, `question_type` (`MCQ`|`Written`), `subject`,
    `source_tag`, `question_text`, `options` (`{}` for Written, or a/b/c/...),
    `answer`, `solution`, `page_number`
- Output: `output_questions.json` (same MCQ schema as before, plus `subject`)

## What this does

1. **Ingest** all `documents/*.txt` (and legacy `*.json`) into a local vector KB (not Chemistry-only).
2. **Retrieve** top-k similar units for each skill/topic/Bloom/`subject` tuple.
   - Soft subject boost only (never hard-filters out other subjects).
3. **Generate** new MCQs with local Ollama.

## Tuple format for ontology teammate

See [TUPLE_FORMAT.md](TUPLE_FORMAT.md). Same as before + required `subject` field.

## Setup

From `data-gen/`:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install [Ollama](https://ollama.com), then:

```powershell
ollama pull qwen2.5:7b-instruct-q4_K_M
# If 4GB VRAM is too tight / too slow:
ollama pull qwen2.5:3b-instruct
$env:OLLAMA_MODEL = "qwen2.5:3b-instruct"
```

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

# 3) Generate questions (needs new tuples.json with subject field)
python generate_question_rag.py
```

## Config knobs

See `config.py`:

- `EMBEDDING_MODEL_NAME` (default multilingual MiniLM)
- `TOP_K`, `SUBJECT_MATCH_BOOST`
- `OLLAMA_MODEL`, `N_QUESTIONS`, `START_TUPLE_INDEX`
