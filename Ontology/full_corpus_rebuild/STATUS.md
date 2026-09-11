# Full-Corpus Ontology Rebuild — Status

**State: consolidated and validated. ALL CHEMISTRY IS DONE — both `ChemBook1.txt`
(731 records) and `ChemBook2.txt` (957 records) are fully processed. Mathematics
and Physics are still entirely unprocessed.**

## What's actually in `tuples.json` / `prereqs.json` right now

Extracted from **all 1,688 Chemistry records** — `ChemBook1.txt` (chunks b01–b06)
and `ChemBook2.txt` (chunks b07–b09). That is **37.7% of the full 4,474-record
corpus**. Still at 0%: `MathBook1` (802), `MathBook2` (605), `PhyBook1` (615),
`PhyBook2` (764).

| | after b01–b04 | after b05–b06 | **now (b01–b09)** |
|---|---|---|---|
| Records processed | 480 | 731 | **1,688** |
| Skills | 388 | 514 | **843** |
| Prerequisite edges | 109 | 199 | **348** (345 after transitive reduction) |
| Unresolved prereq mentions | 50 | 46 | **46** |
| Legacy skillIds reused | 4 | 10 | **24** |
| Topics (raw / canonical) | 25 / 25 | 26 / 25 | **30 / 27** |
| Max DAG depth | 3 | 4 | **4** |

### Per-chunk contribution

| Chunk | Records | New skills minted | References to existing skills |
|---|---|---|---|
| b05+b06 (`ChemBook1` 481–731) | 251 | 123 | 75 |
| b07 (`ChemBook2` 1–320) | 320 | 189 | 32 |
| b08 (`ChemBook2` 321–640) | 320 | 99 | 60 |
| b09 (`ChemBook2` 641–957) | 317 | 32 | 35 |

The falling mint rate across b07 → b08 → b09 is the reuse rule working as
intended: b07 opened up gas laws and organic chemistry from almost nothing, and
by b09 (volumetric analysis and redox, heavily repeated from b08) only
electrochemistry was genuinely new.

## Validation

`python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --config Backend/tree_data/ontology_config.json --report-only -v`
(full output in `validation_report.txt`): **valid DAG, no cycle**, 843 skills,
345 edges after transitive reduction (3 redundant dropped), 27 canonical topics,
max depth 4.

Data-integrity sweep, clean: no duplicate skillIds, no invalid Bloom levels, no
short/empty descriptions, no dangling or self prerequisite edges, no stale
prerequisite description text, and **no backslashes anywhere** in any skill
description (the LaTeX-escaping hazard from `HANDOFF2.md` §2 stays avoided by
writing every formula in plain text — `sqrt`, `delta`, `^`).

Bloom spread across all 843: Apply 352, Remember 290, Understand 137, Analyze 51,
Evaluate 11, Create 2.

The "3 topics not in any section" and "42 unknown topics" / "empty sections"
warnings are the expected noise documented in `HANDOFF3.md` — the course catalog
expects Math/Physics topics this Chemistry-only output does not have yet.

### Legacy topic prefixes are safe

Adopting legacy skillIds brings legacy topic codes (`CHEM_GAS`, `CHEM_GASLAW`,
`CHEM_KINETICS`, `CHEM_ELECTROCHEM`) in with them. All four are already aliased
in `Backend/tree_data/ontology_config.json`, which is why the build tool reports
30 raw topics collapsing to 27 canonical ones. No stray topics were created.

## Tooling in this directory

- `_consolidate_incremental.py` — **use this, not `_consolidate_chembook1.py`.**
  Merges a batch into the existing output, keeps already-assigned ids stable,
  allocates new ids that collide with neither the rebuild nor the legacy
  ontology, adopts legacy-only ids that a batch reuses, resolves prerequisites,
  and re-checks `unresolved_prereqs.json` against the newly added skills.
  Edit `CAND_FILES` at the top for each batch.
- `_find_near_dupes_b07.py` / `_b08` / `_b09` — near-duplicate detector; compares
  new candidates against each other, against the consolidated rebuild, and
  against the legacy Chemistry set. Copy and edit `CAND_FILES` for the next batch.
- `_find_near_dupes.py`, `_consolidate_chembook1.py` — the original b01–b04
  tools, kept only as a historical record. **Do not run `_consolidate_chembook1.py`.**
- `source_issues.json` — 16 records where the source book's own answer key or
  worked solution is wrong or self-contradictory (see `HANDOFF4.md` §5).

## What's NOT done yet

- `MathBook1.txt` (802) and `MathBook2.txt` (605) — Mathematics entirely
  unprocessed. This is the natural next unit and it unblocks the cross-subject
  prerequisites.
- `PhyBook1.txt` (615) and `PhyBook2.txt` (764) — Physics entirely unprocessed.
- Cross-subject prerequisite resolution — still impossible until Mathematics and
  Physics have content. Several of the 46 remaining unresolved mentions wait on
  exactly this; none of them currently matches anything in the ontology even at a
  0.50 similarity threshold, so they are genuinely waiting on new content rather
  than being missed links.
- The exhaustive legacy-id reuse check across *all* Chemistry topics. Much
  improved (all 117 legacy Chemistry skills are scanned automatically every
  batch, and the gas-law, kinetics, thermochemistry and electrochemistry families
  were additionally read by hand, which is how 14 further legacy ids were picked
  up) but still not a full pairwise diff.
- The independent quality-audit pass — never reached. Now worth doing: Chemistry
  is complete enough to sample meaningfully.
- The editorial decision on the 3 proposed new topics (`CHEM_LAB`,
  `CHEM_NUCLEAR`, `CHEM_DESCRIPTIVE`). Unchanged — no new topics were proposed in
  b07–b09 — but it now blocks **58 skills** from appearing in the catalog.
