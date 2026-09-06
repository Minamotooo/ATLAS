# ATLAS — Handoff 2

Read `HANDOFF.md` first — it's still the ground truth for the engine, the ontology,
and the overall project shape. This document only covers what changed **after**
that handoff: the local-Ollama generation attempt was scrapped, replaced with a
Gemini-API pipeline, the ontology got synced to Supabase, and a real chunk of the
question bank has now been generated, verified, and loaded live.

---

## 1. What's different since HANDOFF.md

| Piece | HANDOFF.md said | Now |
|---|---|---|
| Ontology in Supabase | not yet synced | **synced** — old (BCS-era) ontology rows left untouched, new admission-test rows added alongside them |
| Question generation | local Ollama, blocked on hardware | **Ollama code removed entirely.** Generation now runs against the **Gemini API**, key-pooled across multiple keys |
| Question bank | empty | **in progress, and partially live**: 1,034 generated + verified questions are already loaded into Supabase; generation of the remaining tuples is ongoing |
| KB corruption | not mentioned | found and fixed (see §4) |

**Nothing about the Backend/Frontend/engine changed.** If you already know the
adaptive engine, skip straight to §2/§3 below.

---

## 2. Why Ollama got dropped

Local Ollama generation (7B/3B quantized models on a non-GPU laptop) had two
problems, not just one:

1. **Too slow.** ~4–6k prompt tokens + ~3k generated tokens per call, 2,580 calls
   -> multiple weeks on CPU.
2. **A silent JSON-escape corruption bug.** LLMs correctly write LaTeX like `\tan`,
   `\frac`, `\therefore` — but they don't double the backslash the way strict JSON
   requires. `json.loads()` doesn't raise on this: for the subset of letters that
   happen to be legal JSON control escapes (`\b \f \n \r \t`), it just silently
   *consumes* the backslash and replaces it with a control byte, invisibly mangling
   the text. This corrupted both the retrieval knowledge base and generated
   questions and took real effort to root-cause. It is now fixed everywhere it can
   occur (see `question_gen_common.repair_llm_json_escapes()`, applied before every
   `json.loads()` in both the KB ingest and the generator) — **but keep it in mind
   if you touch either of those code paths.**

Switching to the Gemini API (`gemini-3.5-flash-lite` for generation,
`gemini-3.1-flash-lite` for verification) fixed the speed problem outright and
reduced (but did not eliminate — same fix still applies) the corruption rate.

All Ollama code (`generate_question_rag.py`, `smoke_test_rag.py`, the `OLLAMA_*`
settings in `rag/config.py`) has been deleted from the repo. If you still have a
local Ollama install from before, it's untouched and irrelevant now — nothing in
the repo calls it anymore.

---

## 3. The Gemini generation pipeline

### Setup

```bash
cd data-gen
python -m venv .venv && .venv/Scripts/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Build the retrieval KB from documents/*.txt (one-off, a few minutes)
python -m rag.ingest
python -m rag.retriever      # sanity-check retrieval across subjects
```

You also need `keys/.gemini_keys` at the **repo root** (gitignored, not in the
repo) — one Gemini API key per line. Ask whoever ran the last batch for the key
list, or get your own free-tier keys from Google AI Studio. More keys ~linearly
raises throughput: each (key, model) pair gets its own independent rate limit, and
the pipeline round-robins across all of them concurrently.

### How it works

For each (skill, Bloom-level) tuple:

1. **Generate** — retrieve the top-k relevant reference items from the local KB,
   prompt the production model for N MCQs grounded in that material.
2. **Batch-verify** — a *different, cheaper* model independently re-checks each
   generated question: (a) is it actually on-topic for the claimed skill, and
   (b) does a **blind re-solve** (no access to the marked answer or explanations)
   agree with the marked correct option. Several tuples' questions are packed into
   one verification call to cut API call count. Only questions that pass both
   checks get written out.

This two-model split (cheap model verifies, production model generates) and the
blind-re-solve design are deliberate: letting a model grade its own output biases
toward false confidence, and folding verification into the generation call itself
would do the same. An independent judge model, given no hint of which answer was
marked correct, is a real check.

Rate-limited (HTTP 429) keys back off adaptively (increasing delay) and keep
retrying — they are **never** permanently disabled for a rate limit alone. Only an
actual 401/403 (the whole key/project blocked) retires a key for the rest of the
run. If you see "N keys, all exhausted" immediately after starting, something is
wrong — that used to be a bug (fixed) where transient 429s got mistaken for
permanent blocks.

### Running it

```bash
cd data-gen
python generate_question_gemini.py --limit 6              # tiny pilot, cheap test model
python generate_question_gemini.py --sample-topics 5       # broader pilot, cheap test model
python generate_question_gemini.py --batch-size 200 --real # real run, production model

python check_progress.py    # progress %, questions stored, ETA — safe to run anytime
```

- The full tuple space is 430 skills × 6 Bloom levels = **2,580 tuples**.
  `--batch-size N` processes the next N not-yet-done tuples each time you invoke
  it — a full run is just re-invoking with `--real --batch-size <N>` until
  `check_progress.py` says 100%. There's no harm in smaller, repeated invocations;
  it resumes from `gemini_progress.json` automatically.
- Writes happen incrementally per finalized tuple (`output_questions_gemini.json`,
  `gemini_progress.json`) — **safe to kill and resume**, nothing gets corrupted
  mid-write. A killed run just loses whatever was still in-flight, which gets
  redone next time.
- `output_questions_gemini.json` accumulates **all** verified-good questions
  regardless of whether they came from a `--limit`/`--sample-topics` pilot or a
  `--real` run — a question that passed verification is real usable data, there's
  no separate throwaway file anymore.
- These generated files are gitignored on purpose (see `.gitignore`) — they're
  per-machine run state, not source. If you're continuing generation, you're
  starting `gemini_progress.json` from scratch on your machine (0/2580) unless
  someone hands you the current file directly.

### Loading into Supabase

```bash
cd data-gen
python load_questions_to_supabase.py --input output_questions_gemini.json --dry-run
python load_questions_to_supabase.py --input output_questions_gemini.json --create-missing-skills
```

Needs `Backend/.env` with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`. The loader
validates every DB constraint before writing, normalizes Bloom-level casing,
resolves the raw topic strings the LLM writes to canonical `ontology_topics` codes,
and **dedups against what's already in the DB** (safe to re-run after every new
batch of generation — already-loaded questions are skipped, not duplicated).
Always run `--dry-run` first; it prints a full validation report before anything
is written.

---

## 4. Knowledge-base corruption (already fixed, know the shape of it)

The retrieval KB (`data-gen/rag/kb/items.jsonl`, built from `documents/*.txt`, not
tracked in git — rebuild with `python -m rag.ingest`) had the same JSON-escape bug
described in §2, baked into some source records. It was fixed at the source
(`rag/ingest.py`'s escape-repair now runs *before* the first parse attempt, not
just as an exception fallback, since the corruption never raises) and a handful of
already-corrupted records were hand-patched. If a future KB rebuild ever shows
`\neq`/`\nu`-type physics/math symbols rendering as a bare newline or a stray `eq`
in the middle of a solution string, that's this bug resurfacing — check
`rag/ingest.py`'s `repair_json_escapes()`.

---

## 5. Current data state (as of this writing — check live for current numbers)

- **Supabase `questions` table: 2,848 rows total** — the pre-existing 1,814
  legacy/BCS-era rows (untouched, not deleted) **plus 1,034 new admission-test
  questions** generated and verified through this pipeline.
- **Generation progress: run `python data-gen/check_progress.py`** for the live
  number — this is a long-running background process, the count changes
  continuously. Rough progress at last check was ~460/2,580 tuples (~18%).
- **Ontology in Supabase**: synced (`Backend/tree_data/sync_ontology_to_supabase.sql`,
  insert-only — nothing about the old ontology was touched or removed).

**To continue generation:** just keep re-running
`generate_question_gemini.py --real --batch-size <N>` (any batch size, 150–250 is
a reasonable chunk) until `check_progress.py` shows 2,580/2,580, spot-checking
output quality between batches, then run the Supabase loader again to pick up
whatever's new. There is no single "resume" flag needed beyond that — the
progress file handles resumption.

---

## 6. Updated file layout (data-gen/)

```
data-gen/
  rag/
    config.py                   paths + hyperparameters (Ollama settings removed)
    ingest.py                   documents/*.txt -> rag/kb/items.jsonl
    embeddings.py, retriever.py retrieval
    README.md
  question_gen_common.py        shared prompts, ontology loading, Bloom expansion,
                                 schema/LaTeX validation (used by the generator)
  generate_question_gemini.py   Gemini generation: key pool, generate + batch-verify
  check_progress.py             progress %/ETA for a running or paused batch
  load_questions_to_supabase.py question bank loader (unchanged in behavior)
keys/.gemini_keys                Gemini API keys, one per line — gitignored, get
                                  this from whoever ran the last batch, or make your own
```

`generate_question_rag.py`, `smoke_test_rag.py`, and the Ollama config knobs are
gone — don't look for them.
