# Full-Corpus Ontology Rebuild — Status

**State: partial, consolidated, validated. Chemistry only, ~66% of one book.**

## What's actually in `tuples.json` / `prereqs.json` right now

Extracted from **`ChemBook1.txt` records 1–480 of 731** (chunks b01–b04 of the
6 planned for that book). That is **~10.7% of the full 4,474-record corpus**
(`ChemBook2`, `MathBook1`, `MathBook2`, `PhyBook1`, `PhyBook2` — **0% processed**).

| | |
|---|---|
| Raw candidate skills extracted | 402 |
| After dedup/consolidation | **388** |
| Legacy skillIds reused (genuine match found) | 4 (`CHEM_AT1`, `CHE_ATOMIC2`, `CHEM_ATOMIC5`, `CHEM_REDOX2`) |
| Resolved prerequisite edges | 109 (2 further dropped as redundant by the build tool) |
| Unresolved prerequisite mentions | 50 — see `unresolved_prereqs.json`. Mostly dependencies on skills outside this partial batch (other Chemistry chapters not yet processed, or foundational Math). Not dropped, not guessed — logged for later resolution once more of the corpus is processed. |
| New topics proposed (not yet in the 66-topic canonical list) | 3 — see `new_topics_proposed.json`: `CHEM_LAB` (Laboratory Techniques and Safety), `CHEM_NUCLEAR` (Nuclear Chemistry), `CHEM_DESCRIPTIVE` (descriptive/qualitative inorganic chemistry facts). Need an editorial decision in `Backend/tree_data/ontology_config.json` before they can appear in the catalog. |

Validated against this project's own tooling
(`python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --report-only -v`,
full output in `validation_report.txt`): **valid DAG, no cycle**, 107 edges after
transitive reduction, 25 topics, max depth 3 (shallow — expected, since only one
book's coverage exists so far, so prerequisite chains can't yet run very deep or
cross into other topics/subjects).

The "44 unknown topics" / "empty sections" warnings in `validation_report.txt` are
expected noise from the *existing* course/section catalog (`ontology_config.json`)
expecting Math/Physics/Chemistry topics that simply aren't in this partial output
yet — not a real problem.

## How the consolidation worked (for anyone continuing this)

1. `candidates/ChemBook1_b0{1-4}.json` — raw per-chunk extraction output (as
   originally designed in the now-stopped workflow).
2. Near-duplicate detection: `_find_near_dupes.py` (Jaccard word-overlap within
   each topic) flagged 25 candidate pairs; each was read and judged by hand —
   13 were genuine duplicates (merged), the rest were legitimately distinct
   skills that just share vocabulary (e.g. "calculate neutrons from mass number
   and atomic number" vs the converse "calculate atomic number from mass number
   and neutrons" — different unknowns solved for, kept separate; "recall a
   formula exists" vs "apply that formula" — different Bloom levels, kept
   separate).
3. `_consolidate_chembook1.py` — encodes those 13 merge decisions plus 4
   legacy-skillId reuses as data, mechanically unions `sourceItemIds`, assigns
   final `skillId`s (new sequential numbers under existing topic prefixes,
   checked against `Ontology/tuples.json` for collisions), and resolves
   `prereqs` edges (direct where `toTempId` was in the same chunk, fuzzy
   description-match otherwise, unresolved and logged rather than guessed).
4. Legacy-reuse checking was **not exhaustive** — only the topics with the
   highest overlap likelihood (`CHE_ATOMIC`/`CHEM_AT` family, `CHEM_REDOX`) were
   cross-checked against the legacy ontology's 117 Chemistry skills. The other
   ~20 topics used here were not individually diffed against all 117 legacy
   entries — a known gap, not an oversight to be alarmed by, just not yet done.

## What's NOT done yet

- `ChemBook1.txt` records 481–731 (chunks b05–b06).
- All of `ChemBook2.txt`, `MathBook1.txt`, `MathBook2.txt`, `PhyBook1.txt`,
  `PhyBook2.txt` — i.e. Mathematics and Physics are completely unprocessed.
- Cross-subject prerequisite resolution (e.g. a Chemistry stoichiometry skill
  depending on a Math skill) — impossible until Mathematics has any content.
- The quality-audit pass (independent fresh-eyes review) from the original
  workflow design was never reached.

## Why this stopped here

The original design ran ~40 concurrent/sequential subagent calls per book via
the `Workflow` tool. That burned tokens and tripped an account-level session
usage limit before getting far. This partial batch was consolidated **directly**
(no subagent spawned) specifically to avoid repeating that cost while figuring
out a cheaper way to process the rest — see the conversation for the follow-up
plan on that.
