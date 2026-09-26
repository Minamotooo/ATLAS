# Prompts

Every prompt that shaped ATLAS's content, in the order the pipeline runs them.

This directory is the consolidated record: what was asked of a model, why it was
asked that way, and what each prompt produced. Each file opens with a header
giving its purpose, where it lives in code (if it is live), and the design
decisions behind it.

---

## The pipeline

```
   HSC/NCTB syllabus
          │
          ▼
   ┌──────────────┐
   │ 01 taxonomy  │  syllabus → 51 chapters, 183 topic codes
   └──────┬───────┘
          ▼
   ┌──────────────┐      ┌──────────────┐
   │ 02 system    │  +   │ 03 task      │  4,474 exam records → 1,688 skills
   │   (rules)    │      │  (workflow)  │
   └──────┬───────┘      └──────────────┘
          ▼
   ┌──────────────┐
   │ 04 editorial │  retag · author · split · dedupe · validate · connect
   └──────┬───────┘
          ▼
   ══════ ONTOLOGY COMPLETE — 1,688 skills, 1,743 edges, 183/183 topics ══════
          │
          ▼
   ┌──────────────┐      ┌──────────────┐
   │ 05 system    │  +   │ 06 user      │  each (skill × Bloom) → MCQs
   │   (rules)    │      │  (per tuple) │
   └──────┬───────┘      └──────────────┘
          ▼
   ┌──────────────┐
   │ 07 verify    │  relevance judge + blind re-solve → accept / reject
   └──────┬───────┘
          ▼
     question bank → database → app
```

---

## What each file is for

| # | File | Purpose |
|---|---|---|
| **01** | `01_taxonomy_from_syllabus.md` | Turns the official HSC/NCTB syllabus into the fixed 183-topic vocabulary everything else is filed against. Runs once, before extraction. |
| **02** | `02_ontology_extraction_system.md` | Standing rules for the extraction model: the Bloom table, reuse-before-minting, prerequisite density, the closed topic vocabulary, JSON escaping. |
| **03** | `03_ontology_extraction_task.md` | The working instruction: parse the corpus, batch it, extract 2–5 skills per record, find prerequisites *against the accumulated ontology*. Includes the worked example and the per-batch quality gate. |
| **04** | `04_ontology_editorial_qa.md` | The cleanup that turns raw extraction into a usable graph. Six passes: retag, author foundations, split fused skills, deduplicate, validate, connect fragments. |
| **05** | `05_question_generation_system.md` | Standing rules for the MCQ writer: MCQ-only, Bangla output, LaTeX discipline, distractor design. **Live** — mirrors `question_gen_common.py`. |
| **06** | `06_question_generation_user.md` | The per-tuple message: skill, Bloom level, prerequisite chain, and retrieved real exam items for grounding. **Live.** |
| **07** | `07_question_verification.md` | The quality gate: an independent model judges whether each question tests its stated skill, and blind-re-solves it to check the answer key. **Live.** |
| **08** | `08_legacy_extraction_prompt.md` | The superseded prompt that built the original 430-skill ontology. Kept because the delta between it and 02/03 is the project's clearest evidence of iteration. |

**"Live"** means the prompt is a copy of a string in running code. The code is
the source of truth — change one, change both.

---

## Reading order

**For a supervisor or examiner** — `01` → `02` → `08`.
`01` shows the taxonomy is externally anchored rather than invented; `02` shows
the extraction constraints; `08` shows what changed and why, with measurements.

**For someone picking up the project** — this file → `ATLAS/HANDOFF5.md` → then
whichever stage you are at.

**For someone generating questions next** — `05` → `06` → `07`, and read
`HANDOFF5.md §5` first for the one config change that must happen before a run.

---

## Two results worth knowing

Both are measured, not claimed, and both are the kind of thing a prompt-design
question deserves as an answer.

**1. Adding one constraint changed the output structurally.**
Chemistry was extracted first, under a prompt that asked whether anything
*within a record* depended on anything else in that record. The corpus yields
~1.2 skills per record, so the answer was almost always no. Result: 843 skills,
**0.47 edges per skill, 44% of skills with no prerequisite at all** — a DAG in
name only.

Diagnosis is in `Ontology/full_corpus_rebuild/prereq_sparsity_diagnosis.md`. The
fix was Global Constraint 4 in prompt `02`, which replaces the within-record
question with: *of everything extracted so far, what must a learner already
hold?*

Every one of the **18 batches** run afterwards came in above **1.0 edges per
skill with zero isolated skills**. No other change was made.

**2. Mechanical quality checks over-flagged by roughly 2×, twice.**

| Check | Flagged | Real after review |
|---|---|---|
| Multi-action skill regex | 173 | 47 |
| Bloom-inversion edges | 147 | 3 |
| Fragment-link proposals (first heuristic) | 83 | ~33 usable |

The Bloom-inversion case is the instructive one: the *check* was wrong, not the
data. `MAT_MATRIX16` ("Remember: a determinant with two equal rows is zero")
requiring `MAT_MATRIX13` ("Apply: evaluate a 3×3 determinant") is the correct
order — Bloom tier measures cognitive demand, not teaching sequence.

The working rule this produced, recorded in prompt `04`: **run the heuristic,
then read every hit.**

---

## Not in this directory

- **The syllabus itself** — pasted in during the taxonomy session; the
  structure it produced lives in `Backend/tree_data/build_syllabus_config.py`.
- **Per-batch extraction scripts** — mechanical emitters, not prompts.
- **Editorial decision tables** — the actual per-skill judgements from stage
  `04` live inline in `Ontology/full_corpus_rebuild/_*.py`, which is
  deliberate: the table is the deliverable, and a diff is not reviewable
  without it.
