# 03 — Ontology extraction: TASK prompt

> **What this is.** The working instruction that drives the extraction run.
> Pair it with prompt `02`, which must be loaded first as the system message.
>
> **Techniques in use.** Chain-of-Thought · Output Structuring · Constraint
> Setting · Iterative Batch Processing with Checkpointing.
>
> **When it runs.** Once per session, repeatedly, across many sessions. This job
> does not fit in one context window and is not meant to.
>
> **What it produced.** 27 batches (`b01`–`b27`) covering all 4,474 records →
> 1,688 skills, 1,743 prerequisite edges, all 183 syllabus topics populated.
>
> **Provenance.** Adapted from `Ontology/ontology_rebuild_actual_prompt.md`. The
> one substantive change: the canonical-topic section now points at the
> 183-topic syllabus taxonomy (prompt `01`) rather than listing the legacy 66
> codes. Batches b01–b12 ran under the legacy vocabulary and were re-filed
> afterwards by the retag pass in prompt `04`; b13 onward used syllabus codes
> directly. The worked example has been updated to match.

---

## Instruction

You are OntologyGPT — load `02_ontology_extraction_system.md` first; it defines
your persona, the Bloom table, the reuse rule, the prerequisite-density
constraint and the JSON-escaping rule this task depends on.

Your job: **build the Mathematics / Physics / Chemistry skill ontology from the
full `documents/*.txt` corpus (~4,474 records)**, filed against the fixed
183-topic HSC syllabus taxonomy.

This is a multi-session batch job. Work the steps in order and checkpoint after
every batch so a later session resumes exactly where you stopped.

---

## Step 0 — Parse the corpus (do not write your own parser)

`data-gen/rag/ingest.py::load_document_items()` already parses this exact corpus
correctly, including two real corruption fixes you must not reimplement:
`repair_json_escapes()` (LaTeX-backslash repair) and `salvage_objects()`
(resynchronises past a corrupt record instead of losing the surrounding array —
this cost 334 real Chemistry records once; see `HANDOFF2.md` §4).

```bash
cd data-gen
python -c "
import sys; sys.path.insert(0, '.')
from rag.ingest import load_document_items
import json
items = load_document_items()
print(f'{len(items)} items total')
with open('../Ontology/full_corpus_rebuild/parsed_items.jsonl', 'w', encoding='utf-8') as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + '\n')
"
```

Needs only `numpy` — **not** `torch`/`sentence-transformers`. Import
`load_document_items` directly rather than running `python -m rag.ingest`, which
also builds embeddings you do not need.

**Confirm the total is near ~4,474 before extracting a single skill.** If it is
wildly different, stop and check whether `documents/` has changed.

## Step 1 — Set up the workspace (the legacy ontology stays untouched)

Create `Ontology/full_corpus_rebuild/` holding:

| File | Contents |
|---|---|
| `parsed_items.jsonl` | Step 0 output, one record per line, each with an `item_id` |
| `tuples.json` | the skill list — starts `[]` |
| `prereqs.json` | the prerequisite map — starts `{}` |
| `progress.json` | `{processed_item_ids, files_completed, skills_so_far, last_updated}` |
| `rebuild_report.md` | running notes: proposed topics, unmappable records, suspected corruption |

**Do not modify** `Ontology/{tuples,prereqs,skill_ontology_dag.html}.json` or
anything under `Backend/tree_data/`. Those are the legacy ontology and the live
compiled catalog — read-only. Whether and when this rebuild replaces them is a
separate human decision.

## Step 2 — Batch plan

Process one source file at a time, smallest concept-surface first so the
accumulated skill set is warm before the two largest files:

```
MathBook2 → PhyBook1 → ChemBook1 → PhyBook2 → MathBook1 → ChemBook2
```

Sub-batch every **150–250 records**. After each sub-batch, merge, checkpoint,
and print a one-line tally. Never hold more than one un-merged batch.

## Step 3 — Per-record extraction

For each record:

1. **Read everything** — `question_text`, plus `options`, `answer` and
   `solution` where present. The worked solution often reveals sub-skills the
   stem alone does not, such as a specific formula rearrangement step.

2. **Extract 2–5 atomic skills.** For each: assign exactly one Bloom level by
   its verb (system prompt table); assign a `topicKey` from the 183-topic
   syllabus taxonomy; and **check the running `tuples.json` for an existing
   equivalent before minting a new `skillId`.**

3. **Identify prerequisites against the accumulated ontology — not against this
   record.** This is the step that has failed before. Do not ask *"does anything
   in this record depend on anything else in this record?"* — mean yield is ~1.2
   skills per record, so that is structurally almost always "no", and asking it
   is exactly what produced a 44%-inert first pass. Ask instead:

   > *Of everything already in `tuples.json`, what must a learner already hold
   > before this new skill is reachable?*

   Search the accumulated skills for that topic **and its obvious upstream
   topics** — stoichiometry under thermochemistry, oxidation numbers under
   redox, bonding under organic mechanisms — before concluding a skill is
   foundational.

---

### Worked example — reuse this exact shape

Record:

```json
{
  "question_number": "01", "question_type": "MCQ", "subject": "Physics",
  "source_tag": "[RUET'12-13]",
  "question_text": "বলের মাত্রার সমীকরণ কোনটি?",
  "options": {"a": "$[MLT^{-2}]$", "b": "$[MLT]$", "c": "$[MLT^{-1}]$", "d": "$[MLT^{-3}]$"},
  "answer": "a",
  "solution": "সমাধান: (a); বল = ভর × ত্বরণ = [M] × [LT^{-2}] = [MLT^{-2}]",
  "page_number": 2
}
```

Extracted — both Remember, because every verb is recall/recognise:

```json
[
  { "bloom": "Remember", "skillId": "PHY1_DIMENSIONS3",
    "skillFull": "Recall the dimensional formula of force.",
    "topicKey": "PHY1_DIMENSIONS", "topicLabel": "Dimensional Analysis",
    "subject": "Physics" },
  { "bloom": "Remember", "skillId": "PHY1_DIMENSIONS4",
    "skillFull": "Recognise the correct dimensional equation for a quantity among several choices.",
    "topicKey": "PHY1_DIMENSIONS", "topicLabel": "Dimensional Analysis",
    "subject": "Physics" }
]
```

Now the prerequisite step. **Note that neither edge comes from inside this
record** — both were found by searching what was already extracted:

```json
{
  "PHY1_DIMENSIONS4": [
    { "id": "PHY1_DIMENSIONS3", "full": "Recall the dimensional formula of force.", "depth": 0 },
    { "id": "PHY1_DIMENSIONS0", "full": "Recall the dimensional formula of a given physical quantity.", "depth": 0 }
  ],
  "PHY1_DIMENSIONS3": [
    { "id": "PHY1_DIMENSIONS0", "full": "Recall the dimensional formula of a given physical quantity.", "depth": 0 }
  ]
}
```

`PHY1_DIMENSIONS0` was minted from a different record hundreds of items earlier.
You only find it by asking *"what must the learner already hold?"* and searching
the accumulated `tuples.json` — never by re-reading this record.

**Two skills, three edges. That ratio is normal.** If a whole batch comes out
near zero edges, you are asking the within-record question. Go back and ask the
accumulated-ontology one.

A skill with genuinely no prerequisite exists — the most foundational recall in
a topic — and for those you emit no key. But that is the exception, not the rule.

---

## Topic vocabulary

Use the **183 syllabus topic codes** from
`Backend/tree_data/build_syllabus_config.py` (see prompt `01`). Structure:

| Subject | Chapters | Topics |
|---|---|---|
| Physics | 21 | 72 |
| Chemistry | 10 | 59 |
| Mathematics | 20 | 52 |
| **Total** | **51** | **183** |

Codes read `SUBJECT+PAPER_CONCEPT` — `PHY2_PHOTOELECTRIC`, `CHE1_REDOX`,
`MAT1_DETERMINANT`. Full code → label → subject mapping lives in
`Backend/tree_data/ontology_config.json` (generated; never hand-edit).

**This vocabulary is closed.** If material fits nowhere, log it under
`new_topics_proposed` in `rebuild_report.md` and move on. Do not invent a code.

---

## Required output

**Per sub-batch:** updated `tuples.json`, `prereqs.json`, `progress.json`, plus
a one-line tally. No other narration.

**Per session end** (finished or checkpointing), append to `rebuild_report.md`:

```
--- rebuild status (as of <timestamp>) ---
  records processed   : <n> / ~4,474
  skills extracted    : <n>
  topics touched      : <n> / 183
  new topics proposed : <n>
  prerequisite edges  : <n>
  edges per skill     : <n.nn>   (target >= 1.0; first Chemistry pass was 0.47)
  skills with no edge : <n> (<n>%)  (target <= 25%; first pass was 44%)
  records skipped     : <n>
```

Followed by a bullet list of proposed topics and skipped records, each with its
`item_id` and a one-line reason.

---

## Quality checklist — self-verify before and after every sub-batch

- [ ] Every candidate skill checked against the current `tuples.json` before
      minting an id — no duplicate atomic skills under different ids.
- [ ] Every Bloom level matches its description's action verb — no Analyze
      label on a Remember verb or the reverse.
- [ ] Every `topicKey` is one of the 183 syllabus codes, or is logged under
      `new_topics_proposed`. Nothing silently invented.
- [ ] **Edges ÷ new skills ≥ 1.0 for this batch.** Compute it and state the
      number. Below 0.8 the batch is not finished — re-walk its skills against
      the accumulated `tuples.json` before merging.
- [ ] **≤ 25% of this batch's skills have zero prerequisites.**
- [ ] No backslashes in any `skillFull`/`full` string — formulas written in
      plain words (`sqrt`, `delta`, `^`).
- [ ] `progress.json` reflects records actually *merged*, not merely attempted.
- [ ] Legacy files and `Backend/tree_data/` untouched.
- [ ] `prereqs.json` entries use `depth: 0` uniformly — real depth is computed
      later by `build_from_ontology.py`.
