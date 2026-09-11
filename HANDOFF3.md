# ATLAS — Handoff 3: Full-Corpus Ontology Rebuild (in progress)

Read `HANDOFF.md` and `HANDOFF2.md` first for the engine/ontology/data-gen ground
truth. This document covers a **separate, still-in-progress initiative**: rebuilding
the skill ontology from the *full* `documents/` corpus instead of the small sample
the current 430-skill ontology was built from. It is not finished. This is the
exact state to resume from, what's been tried, what worked, what didn't, and why.

**If you are a fresh agent picking this up: read this whole document before doing
anything.** The single most important fact in it is in §5 (why the first approach
failed) — repeating that mistake will burn the same budget for the same result.

---

## 1. Why this exists

The live ontology (`Backend/tree_data/ontology_source/`, mirrored at
`Ontology/{tuples.json,prereqs.json,skill_ontology_dag.html}` — **430 skills, 66
topics**) was built by hand-feeding an LLM two small samples: 1,379 HSC physics
questions and a separate 300-question BUET mixed-subject set (see
`Ontology/Work done already.md`). The project's actual corpus is much bigger:
`documents/*.txt` — **6 source books, exactly 4,474 machine-extracted question
records** (verified by parsing, not estimated — see §4). The critique that started
this effort: the legacy ontology is sparse because it was never built from that
full corpus, and its skills aren't granular enough (e.g. "integration by parts"
type composite procedures were never decomposed into their constituent steps).

**Explicit instructions from the project owner, still in force:**
- Build a **new** ontology from the full corpus. The legacy 430-skill ontology is a
  **style/legacy reference only** — read it for granularity calibration and to
  reuse a `skillId` when a new skill is genuinely the same concept, but **do not
  edit it, and do not treat it as a base to build on top of.**
- Skills must be **maximally granular** — decompose composite multi-step
  procedures into atomic steps. The canonical example given: "integration by
  parts" is at least 3 skills (recognizing the form applies, choosing u/dv, then
  solving the resulting simpler integral/algebra) — and that third step very often
  isn't a new skill at all, it's a restatement of an existing Algebra/Calculus
  skill and should reuse it rather than mint a near-duplicate. Apply the same
  decompose-then-check-for-reuse discipline everywhere (physics derivations,
  stoichiometry, equilibrium calculations, trig identities inside geometry, etc.),
  not just calculus.
- Every prerequisite relationship should be identified properly, including
  **cross-subject** ones (a Physics or Chemistry skill depending on a Mathematics
  skill is common and must not be missed just because it's a different subject's
  topic prefix).

---

## 2. Documents created for this effort (all still valid, read them)

| File | What it is |
|---|---|
| `Ontology/ontology_rebuild_system_prompt.md` | The persona, Bloom's-Taxonomy table, granularity rule (with the integration-by-parts example verbatim), reuse-before-minting rule, and the JSON-escaping gotcha (see §6). This is the operative rulebook for extracting skills from this corpus — still correct, still in force. |
| `Ontology/ontology_rebuild_actual_prompt.md` | The original task-shaped prompt: corpus record schema, batch/chunk plan, per-record extraction procedure, canonical topic list, output file contract. Written for a slower, more human-supervised pace than what was actually attempted (see §5) — its *rules* are still correct, its *batch-size assumption* (120 records/chunk) is what needs revising. |
| `Ontology/ontology_extraction_system_prompt.md` | An earlier, more generic version of the same idea (merges your own prompt-writing style from `Ontology/2105066_LoRA/prompts/` with your friend's domain prompt from `Ontology/Work done already.md`). Superseded by the two files above for this specific rebuild; kept for reference, not actively used. |
| `Ontology/Work done already.md` | Your friend's original ad hoc prompts (historical reference only — the small-sample approach these superseded). |

---

## 3. What was actually attempted: a Workflow, and why it's not running anymore

A `Workflow` (`atlas-ontology-rebuild`, 6 phases: Parse → Extract → Merge per
subject → Cross-subject prerequisite resolution → Validate → Quality audit) was
built and launched to process the whole corpus with ~45 subagents (one per
~120-record chunk, plus merge/validate/audit agents). **It was explicitly stopped
by the project owner partway through** because it was burning tokens/hitting
account limits too fast for the value delivered — see §5 for the concrete numbers
and the recommended fix. **Do not just relaunch that same design at the same
chunk size.** The script still exists on disk if you want to see the exact
mechanics that were tried:
`C:\Users\User\.claude\projects\C--Users-User-Downloads-Capstone-ATLAS\a9a81382-ae16-4ca4-8743-4dd886826dd2\workflows\scripts\atlas-ontology-rebuild-wf_b0c5e191-743.js`
— read it for ideas, don't just re-run it unmodified.

---

## 4. Current data state — read this before extracting anything new

Everything lives under `Ontology/full_corpus_rebuild/`. **Coverage: ~10.7% of the
corpus, Chemistry only.** Exact breakdown:

| File | Contents |
|---|---|
| `parsed_items.jsonl` | **All 4,474 corpus records, already parsed. Reuse this — do not re-parse.** One JSON object per line, produced by reusing `data-gen/rag/ingest.py`'s `load_document_items()` (via the helper script `data-gen/_dump_parsed_items.py`, left in place). Exact per-book counts, verified: `ChemBook1` 731, `ChemBook2` 957, `MathBook1` 802, `MathBook2` 605, `PhyBook1` 615, `PhyBook2` 764. Records are grouped contiguously by book in that order (alphabetical glob order, matching `load_document_items()`'s own iteration). |
| `candidates/ChemBook1_b01.json` … `b04.json` | Raw, pre-consolidation extraction output for **`ChemBook1` records 1–480 of 731** (4 of the 6 chunks originally planned for that book, at the old 120-record chunk size). Kept as-is for audit trail — the consolidated result below is what to actually build on. |
| `tuples.json` | **388 consolidated Chemistry skills** — the real, final, deduplicated output for what's been processed so far. This is what a next batch should check against for reuse-before-minting, alongside the legacy `Ontology/tuples.json`. |
| `prereqs.json` | 109 resolved prerequisite edges within this partial batch. |
| `unresolved_prereqs.json` | 50 prerequisite mentions that couldn't be confidently resolved within this partial batch (`{finalSkillId: [{description, topicKeyGuess}]}`) — likely dependencies on Chemistry content not yet processed (records 481–731, or `ChemBook2`) or on Mathematics skills that don't exist yet in this rebuild. **Re-check these against every new batch's output** — don't let them sit forever. |
| `new_topics_proposed.json` | 3 topics used here that aren't in the canonical 66: `CHEM_LAB` (Laboratory Techniques and Safety), `CHEM_NUCLEAR` (Nuclear Chemistry), `CHEM_DESCRIPTIVE` (descriptive/qualitative inorganic facts — reaction prediction, mineral sources, flame tests, etc.). These need a human editorial call in `Backend/tree_data/ontology_config.json` before they can appear in the platform catalog — don't just silently keep minting skills under them without that decision eventually happening. |
| `skipped_items.json` | Empty — nothing was unextractable in this batch. |
| `validation_report.txt` | Output of running this project's own `Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --config Backend/tree_data/ontology_config.json --report-only -v` against the consolidated result: **valid DAG, no cycle**, 107 edges after transitive reduction (2 redundant dropped), 25 topics, max depth 3 (shallow — expected, since coverage is still narrow). The "44 unknown topics" / "empty sections" warnings in it are just the existing catalog expecting Math/Physics/other-Chemistry topics this partial batch doesn't have yet — not a real problem. **Re-run this exact command after every future consolidation** — it's the cheapest, most reliable correctness check available (catches cycles, redundant edges, missing descriptions) and costs one subprocess call, not an agent.|
| `STATUS.md` | A shorter version of this same data-state summary, written right after the consolidation — kept in sync with this handoff, check both if they ever seem to disagree (this handoff is the more complete narrative). |
| `_find_near_dupes.py` | Reusable near-duplicate detector: Jaccard word-overlap between skill descriptions, compared only within the same `topicKey` (cheap, no LLM call). Flags candidate pairs above a similarity threshold for a human/agent to actually judge — it does **not** decide on its own, on purpose, because plenty of high-overlap pairs are legitimately distinct (see §6). Edit the file list at the top and re-run for the next batch. |
| `_consolidate_chembook1.py` | The script that actually did the ChemBook1 b01–b04 consolidation: encodes the specific merge-group and legacy-reuse decisions (from manually judging `_find_near_dupes.py`'s output) as plain data, then mechanically unions `sourceItemIds`, assigns final `skillId`s (checked against `Ontology/tuples.json` for collisions), and resolves `prereqs` edges (direct where possible, fuzzy description-match otherwise, else logged unresolved). **This is a template, not a generic tool** — its `MERGE_GROUPS`/`REUSE_LEGACY` dicts are ChemBook1-b01–b04-specific. Copy it and redo the merge-group analysis for the next batch rather than expecting it to "just work" on new data. |

---

## 5. Why the first approach failed, in concrete numbers — read before choosing chunk sizes

The original workflow chunked the corpus into ~120-record pieces (~38 chunks
total) and gave each one its own subagent, each independently instructed to *read*
both prompt files (`ontology_rebuild_system_prompt.md`,
`ontology_rebuild_actual_prompt.md`) plus two topic-reference JSON files before
doing any actual extraction. Two failures resulted, in this order:

1. **A background-task/session hiccup lost an in-flight run entirely** (likely
   around a `/config workflows=true` toggle — the task ID became untrackable via
   `TaskOutput`/`ListAgents` mid-run). Recovered cleanly via
   `Workflow({scriptPath, resumeFromRunId})` — the cached Parse-phase result
   (all 4,474 items) replayed instantly, confirming the resume mechanism works.
   Worth knowing this can happen, not something to panic about if it does again.
2. **The real failure**: on resume, all ~44 non-cached agent calls failed
   immediately with `"You've hit your session limit"` (an account-level usage
   limit, not a context-window problem). This is a *rate/quota* failure from
   firing many `Task`/subagent calls in bursts (the `Workflow` tool caps
   concurrency at 16 simultaneous agents) — not from any single agent's prompt
   being too large.

**The fix that actually worked**, applied to the 4 chunks that had already
completed: **consolidation was done directly, with zero subagents spawned** —
reading the candidate files and reasoning about duplicates/reuse/prerequisite
resolution in the main session, backed by one cheap mechanical script
(`_find_near_dupes.py`) instead of an LLM-driven "merge" agent. This produced a
real, validated result (§4) at a fraction of the cost.

**Recommended approach for continuing** (not yet implemented — this is the
concrete plan the next batch should follow):
- **Bigger chunks.** 300–400 records per chunk instead of 120, so the fixed
  per-agent overhead (reading reference material) is amortized over more actual
  work. This roughly quarters the number of subagents needed.
- **Inline the ruleset instead of "go read these files."** Every extraction
  prompt should embed the compact Bloom table + granularity rule + reuse rule
  directly as text, rather than instructing the agent to open
  `ontology_rebuild_system_prompt.md`/`ontology_rebuild_actual_prompt.md` itself.
  Two fewer file reads per agent, multiplied across however many chunks remain.
- **Don't fire a 16-wide parallel burst.** Process in small batches (2–4
  concurrent) or fully sequentially. Slower wall-clock, much less likely to
  re-trip the same session limit.
- **Do the merge/consolidation step yourself, not via an agent.** Demonstrated
  above to work well and cheaply. Reserve subagents for the part that actually
  needs a large context window and corpus-reading judgment — raw extraction from
  question records — not for deduplication bookkeeping you can script plus judge
  by hand in a few minutes per batch.

---

## 6. Judgment calls made during consolidation (read before doing the next batch, so decisions stay consistent)

These are real examples from ChemBook1's consolidation, worth knowing so the same
kind of call is made the same way next time:

- **Same fact, different Bloom-level skill → keep separate.** "Recall that max
  electrons in shell n = 2n²" (Remember) and "Calculate max electrons in shell n
  using 2n²" (Apply) look like near-duplicates by word overlap but are genuinely
  different testable skills. Do not merge just because the topic and formula are
  the same.
- **Converse-direction calculations → generally keep separate**, *unless* it's a
  trivial single-equation rearrangement. "Calculate neutrons from mass number and
  atomic number" vs. "calculate atomic number from mass number and neutrons" were
  merged into one skill (both are just rearranging `Z + N = A`for a different
  unknown — genuinely the same underlying skill). But "solve for concentration
  after time t" vs. "solve for time given a target concentration" in first-order
  kinetics were kept **separate**, because the second direction requires an extra
  logarithm step the first doesn't — a real difference in procedure, not just
  which symbol is unknown.
- **A general skill and a named special-case of it → usually merge into the
  general one**, keeping the general wording. E.g. "solve molar solubility
  directly, s=√Ksp, for a 1:1 salt" merged into the general "solve the
  solubility-product expression for molar solubility."
- **A named special-case that requires genuinely different handling → keep
  separate.** "Solve molar solubility from Ksp in the presence of a common ion"
  was kept as its own skill, not merged into the plain solubility-product skill,
  because the common-ion effect requires materially different algebra.
- **Legacy-id reuse was only checked for the highest-overlap topics** (the
  `CHE_ATOMIC`/`CHEM_AT`/`CHEM_ATOMIC` family and `CHEM_REDOX`, against the
  legacy ontology's 117 Chemistry skills) — not exhaustively across all 25 topics
  touched so far. Worth widening this check as more of the corpus is processed,
  especially once Mathematics and Physics start (their legacy skill counts are
  in `Ontology/tuples.json`, filter by `subject`).
- **JSON escaping**: no problems were hit in this batch (the extraction agents
  used proper JSON serializers), but this corpus has a documented history of
  LaTeX-backslash corruption (`HANDOFF2.md` §2, `rag/ingest.py`'s
  `repair_json_escapes()`) — stay alert for it, especially once Physics/Math
  content (much more LaTeX-heavy than the Chemistry processed so far) is
  extracted.

---

## 7. Exact next steps

1. **Finish `ChemBook1`**: records 481–731. Verified directly: `ChemBook1` is
   first in `parsed_items.jsonl`'s file order, so these are literally **absolute
   lines 481–731** of that file (confirmed: line 481 and line 731 are both
   `ChemBook1.txt`, line 732 is the first `ChemBook2.txt` record).
2. **`ChemBook2.txt`** (957 records) — 0% done.
3. Once all of Chemistry is done: re-run the legacy-id-reuse check across *all*
   Chemistry topics (not just the two checked so far), then re-run
   `build_from_ontology.py --report-only` again.
4. **`MathBook1.txt` (802) and `MathBook2.txt` (605)** — Mathematics is entirely
   unprocessed. This unblocks resolving the Chemistry batch's cross-subject
   `unresolved_prereqs.json` entries that plausibly depend on Math skills.
5. **`PhyBook1.txt` (615) and `PhyBook2.txt` (764)** — Physics is entirely
   unprocessed.
6. **Cross-subject prerequisite resolution** — go back through every subject's
   `unresolved_prereqs.json` once all three subjects have content, and resolve
   what can now be matched (this is exactly what the original workflow's
   "Resolve cross-subject prerequisites" phase was designed to do — that design
   is still sound, it just never got reached).
7. **Quality audit** — an independent fresh-eyes pass sampling skills across all
   three subjects for granularity and prerequisite correctness (the original
   workflow's Phase 6). Never reached. Worth doing once there's enough combined
   content to sample meaningfully, not necessarily after every small batch.
8. **Decide on proposed new topics** (`new_topics_proposed.json`, growing as more
   batches run) in `Backend/tree_data/ontology_config.json` — this is a human
   editorial call, not something an agent should decide unilaterally.
9. **Decide how/whether this rebuild replaces the legacy ontology** once it's
   further along — out of scope for now; the legacy files stay untouched in the
   meantime.

Update this document (or a `HANDOFF4.md`, following the existing numbering
convention) as further batches complete — don't let the next agent re-derive all
of this from scratch.
