# Actual Prompt — Rebuild the Ontology from the Full Corpus

## Technique: Chain-of-Thought + Output Structuring + Constraint Setting + Iterative Batch Processing with Checkpointing

---

## Instruction

You are OntologyGPT (see `ontology_rebuild_system_prompt.md` — load it first, it
defines your persona, the Bloom table, the reuse-before-minting rule, and the
JSON-escaping rule this task depends on). Your job: **rebuild ATLAS's Mathematics /
Physics / Chemistry skill ontology from the full `documents/*.txt` corpus
(~4,474 records)**, replacing the legacy 430-skill ontology's *coverage* while
matching its *style*. This is a multi-session batch job — you will not finish it in
one context window, and that's expected. Work through the steps below in order;
checkpoint after every batch so a later session can resume exactly where you left
off.

---

## Step 0 — Parse the corpus without the heavy RAG pipeline

You need parsed records, not embeddings. `data-gen/rag/ingest.py`'s
`load_document_items()` already parses `documents/*.txt` correctly — including two
real corruption fixes you do **not** want to reimplement: `repair_json_escapes()`
(LaTeX-backslash repair) and `salvage_objects()` (resynchronizes past one corrupt
record instead of losing the whole surrounding array, which cost 334 real Chemistry
records once — see `HANDOFF2.md` §4). Reuse it directly instead of writing your own
parser:

```bash
cd data-gen
python -c "
import sys; sys.path.insert(0, '.')
from rag.ingest import load_document_items
import json
items = load_document_items()
print(f'{len(items)} items total')
by_file = {}
for it in items:
    by_file.setdefault(it['source_file'], 0)
    by_file[it['source_file']] += 1
print(by_file)
with open('../Ontology/full_corpus_rebuild/parsed_items.jsonl', 'w', encoding='utf-8') as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + '\n')
"
```

This needs only `numpy` from `data-gen/requirements.txt` (a dependency of
`load_document_items` transitively) — **not** `torch`/`sentence-transformers`; if
the import complains about the embeddings module, isolate `load_document_items` by
importing it directly rather than running `python -m rag.ingest` (which also builds
embeddings you don't need for this task). Confirm the total is close to the ~4,474
figure in the system prompt — if it's wildly different, stop and check `documents/`
hasn't changed, before extracting a single skill.

## Step 1 — Set up the rebuild workspace (legacy stays untouched)

Create `Ontology/full_corpus_rebuild/` containing:
- `parsed_items.jsonl` — from Step 0, one record per line, has an `item_id` you'll
  reference in `prereqs.json`'s provenance if useful.
- `tuples.json` — the new skill list. Starts as `[]`.
- `prereqs.json` — the new prerequisite map. Starts as `{}`.
- `progress.json` — `{ "processed_item_ids": [...], "files_completed": [...], "skills_so_far": <n>, "last_updated": "<ISO timestamp>" }`.
- `rebuild_report.md` — running notes: proposed-new-topics needing editorial
  review, records you couldn't confidently map to any skill (with the record's
  `item_id` and a one-line reason), anything that looked like corpus corruption.

**Do not modify** `Ontology/{tuples.json,prereqs.json,skill_ontology_dag.html}` or
anything under `Backend/tree_data/`. Those are the legacy ontology — read-only,
used only as a style/granularity/topic-code reference (per system prompt Global
Constraint 2). The user decides later whether/how to merge this rebuild in.

## Step 2 — Batch plan

Process one source file at a time, in this order (roughly smallest concept-surface
first, so your accumulated skill set is warmed up before the two largest files):
`MathBook2.txt → PhyBook1.txt → ChemBook1.txt → PhyBook2.txt → MathBook1.txt →
ChemBook2.txt`. Within a file, sub-batch every **150–250 records** (matching the
scale your friend's own manual runs already used successfully — see
`Work done already.md`).

After **every** sub-batch:
1. **Re-read the current `tuples.json`** before extracting the next sub-batch's
   skills — not just to append, but so you can actually check new candidates
   against it (system prompt Global Constraint 3). Loading it into your own
   context each time is the mechanism that makes the reuse rule enforceable.
2. Merge newly-confirmed-new skills into `tuples.json`, new prerequisite edges into
   `prereqs.json`.
3. Update `progress.json`: append the sub-batch's `item_id`s to
   `processed_item_ids`, refresh `skills_so_far` and `last_updated`.
4. Print a one-line tally: `"<file>: <n> records processed this batch, <total>
   skills so far, <m> topics touched."` — this is your own resumoption checkpoint
   as much as it's a progress signal to the user.

If you are ever unsure whether you have enough context budget left to safely do
another full sub-batch-plus-merge cycle, stop after completing and checkpointing
the current one rather than starting a new one you might not finish cleanly. A
resumable partial rebuild is the correct output of an interrupted session.

## Step 3 — Per-record extraction (apply the system prompt's rules)

For each record:
1. Read `question_text` (+ `options`, `answer`, `solution` if present — the
   solution often reveals sub-skills the question stem alone doesn't, e.g. a
   specific formula rearrangement step).
2. Extract 2–5 atomic skills. For each: assign exactly one Bloom level by verb
   (system prompt table); resolve `topicKey`/`topicLabel`/`subject` against the
   canonical topic list below, reusing an existing one whenever the concept fits;
   check the running `tuples.json` for an existing equivalent skill before minting
   a new `skillId`.
3. Identify prerequisites: does this skill require another skill (already known,
   from the legacy ontology, or newly minted earlier in this same run) to make
   sense first? If so, add an entry to `prereqs.json`.

### Worked example (reuse this exact shape)

Record:
```json
{
  "question_number": "01", "question_type": "MCQ", "subject": "Physics",
  "source_tag": "[RUET'12-13]",
  "question_text": "বলের মাত্রার সমীকরণ কোনটি?",
  "options": {"a": "$[MLT^{-2}]$", "b": "$[MLT]$", "c": "$[MLT^{-1}]$", "d": "$[MLT^{-3}]$", "e": "$[MLT^{-4}]$"},
  "answer": "a",
  "solution": "সমাধান: (a); বল = ভর \\times ত্বরণ = [M] \\times [LT^{-2}] = [MLT^{-2}]$",
  "page_number": 2
}
```
Extracted (all Remember — every verb is recall/recognize/identify):
```json
[
  { "bloom": "Remember", "skillId": "PHY_UNITS7", "skillFull": "Recall the dimensional formula of force.", "topicKey": "PHY_UNITS", "topicLabel": "Units, Dimensions and Measurement", "subject": "Physics" },
  { "bloom": "Remember", "skillId": "PHY_UNITS8", "skillFull": "Recognize the correct dimensional equation from multiple choices.", "topicKey": "PHY_UNITS", "topicLabel": "Units, Dimensions and Measurement", "subject": "Physics" }
]
```
No prerequisite entry needed here — both skills are foundational recall, nothing in
this record depends on anything else in it.

## Canonical topics (reuse before minting — same list the legacy ontology uses)

**Mathematics**: MAT_MATRIX, MAT_EQTHEORY, MAT_ALGEBRA, MAT_COMPLEX,
MAT_COORD_LINE, MAT_COORD_CONIC, MAT_INVTRIG, MAT_TRIG, MAT_CALC_DIFF,
MAT_CALC_INTEG, MAT_STATICS, MAT_DYNAMICS, MATH_CALC, MATH_GEOM, MATH_MECH

**Physics**: PHY_UNITS, PHY_VEC, PHY_NEWTON, PHY_PROJ, PHY_CIRC, PHY_ROTATION,
PHY_WORK_ENERGY, PHY_GRAVITATION, PHY_ELASTICITY, PHY_FLUID, PHY_SHM, PHY_WAVE,
PHY_OPTICS_WAVE, PHY_OPTICS, PHY_THERMO, PHY_KINETIC, PHY_ELECTROSTATICS,
PHY_CURRENT, PHY_MAGNETISM, PHY_EM, PHY_AT, PHY_MODERN, PHY_NUCLEAR,
PHY_SEMICONDUCTOR, PHY_SOLID, PHY_MOD, PHY_XRAY

**Chemistry**: CHE_STOICHIOMETRY, CHE_ATOMIC, CHE_BONDING, CHE_GASLAWS,
CHE_THERMOCHEM, CHE_EQUILIBRIUM, CHE_ACIDBASE, CHE_ELECTROCHEM, CHE_ORGANIC,
CHE_BIOMOLECULE, CHE_COORD, CHE_QUAL, CHEM_PERIODIC, CHEM_REDOX, CHEM_SOLID,
CHEM_SOLUTION, CHEM_KIN, CHEM_CAT, CHEM_DBLOCK, CHEM_STEREO, CHEM_NOM,
CHEM_ANALYTICAL, CHEM_ENV, CHEM_SPEC

(Full code → label → subject mapping: `Backend/tree_data/topic_labels.json` +
`topic_subjects.json`, or `ontology_extraction_system_prompt.md`'s reference table
if you want labels inline without opening another file.)

---

## Required Output Structure (per sub-batch and at the end)

Per sub-batch: updated `tuples.json`, `prereqs.json`, `progress.json` (Step 2),
plus the one-line console tally. No other narration needed per sub-batch.

At the end of a session (whether the corpus is fully processed or you're stopping
to checkpoint), append to `rebuild_report.md` a short summary in this shape,
modeled on `build_from_ontology.py`'s own report format so it's directly
comparable to the legacy ontology's numbers:

```
--- rebuild status (as of <timestamp>) ---
  records processed      : <n> / ~4,474
  skills extracted        : <n>   (legacy: 430)
  topics touched          : <n>   (legacy: 66)
  new topics proposed     : <n> (see below)
  prerequisite edges      : <n>
  records skipped         : <n> (reasons below)
```
Followed by a bullet list of any proposed-new-topics and any skipped/ambiguous
records with their `item_id` and a one-line reason.

---

## Quality Checklist (self-verify before/after every sub-batch)

- [ ] Checked every candidate new skill against the current `tuples.json` before
      minting a new `skillId` — no duplicate atomic skills under different ids.
- [ ] Every skill's Bloom level matches its description's action verb (system
      prompt table) — no Analyze-tier label on a Remember-tier verb or vice versa.
- [ ] Every topic used is either from the canonical list above or explicitly logged
      under `new_topics_proposed` in `rebuild_report.md` — nothing silently
      invented.
- [ ] Every LaTeX backslash in every `skillFull`/`full` string is doubled.
- [ ] `progress.json` reflects exactly the records actually merged into
      `tuples.json`/`prereqs.json` this batch — not just "attempted."
- [ ] Legacy files (`Ontology/{tuples.json,prereqs.json,skill_ontology_dag.html}`,
      everything under `Backend/tree_data/`) are untouched.
- [ ] `prereqs.json` entries use `depth: 0` uniformly (matching the existing
      convention — real depth is computed later by `build_from_ontology.py`).
