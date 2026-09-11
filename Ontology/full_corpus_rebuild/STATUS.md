# Full-Corpus Ontology Rebuild — Status

**State: partial, consolidated, validated. Chemistry only — `ChemBook1.txt` is now
100% complete; `ChemBook2` and all of Mathematics/Physics remain unprocessed.**

## What's actually in `tuples.json` / `prereqs.json` right now

Extracted from **all 731 records of `ChemBook1.txt`** (chunks b01–b06). That is
**16.3% of the full 4,474-record corpus** (`ChemBook2` 957, `MathBook1` 802,
`MathBook2` 605, `PhyBook1` 615, `PhyBook2` 764 — all **0% processed**).

| | after b01–b04 | **now (b01–b06)** |
|---|---|---|
| Records processed | 480 / 731 | **731 / 731** |
| Skills | 388 | **514** |
| Resolved prerequisite edges | 109 | **199** (196 after transitive reduction) |
| Unresolved prerequisite mentions | 50 | **46** |
| Legacy skillIds reused | 4 | **10** |
| Topics (raw / canonical) | 25 / 25 | **26 / 25** |
| Max DAG depth | 3 | **4** |

The b05+b06 batch contributed 124 candidate skills, of which **123 were minted as
new** and 1 was merged away during review; a further **75 references** from those
same records resolved to skills that already existed (47 to already-consolidated
skills, 28 to skills minted earlier in the same batch). Reuse-before-minting is
working: roughly a third of everything these 251 records exercise was already in
the ontology.

Legacy ids reused this batch (6 new, bringing the total to 10):
- **Adopted into the rebuild** because the concept recurred and the legacy entry
  already said it: `CHEM_KIN1` (units of a rate constant from reaction order),
  `CHEM_KINETICS1` (which plot is linear for a first-order reaction), `CHEM_CAT1`
  (role of a promoter).
- **Taken by a newly-extracted skill** that turned out to be the same concept:
  `CHE_EQUILIBRIUM3` (Kp↔Kc conversion), `CHE_THERMOCHEM1` (q = m·c·ΔT),
  `CHEM_EQ1` (Le Chatelier pressure shift).

`CHEM_KINETICS` is already aliased to `CHEM_KIN` in
`Backend/tree_data/ontology_config.json`, so adopting `CHEM_KINETICS1` does not
create a 26th catalog topic — the build tool merges it.

## Validation

`python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --config Backend/tree_data/ontology_config.json --report-only -v`
(full output in `validation_report.txt`): **valid DAG, no cycle**, 514 skills,
196 edges after transitive reduction (3 redundant dropped), 25 canonical topics,
max depth 4.

Data-integrity sweep also run and clean: no duplicate skillIds, no invalid Bloom
levels, no empty/short descriptions, no dangling or self prerequisite edges, no
stale prerequisite description text, and **no backslashes at all** in any skill
description (the LaTeX-escaping hazard from `HANDOFF2.md` §2 was avoided by
writing formulas in plain text — `sqrt`, `delta`, `^`, as the earlier batches did).

The "3 topics not in any section" and "44 unknown topics" / "empty sections"
warnings are the expected noise documented in `HANDOFF3.md` — the existing
course catalog expects Math/Physics topics this Chemistry-only output does not
have yet. Not a real problem.

## New in this batch

- `candidates/ChemBook1_b05.json`, `candidates/ChemBook1_b06.json` — raw
  extraction output for records 481–731, in the same schema as b01–b04 plus three
  additions: `reusedExistingSkills` (records that exercise an
  already-consolidated skill), `reusedBatchSkills` (a later chunk reusing an
  earlier chunk's skill), and `legacyIdReuse` (a new skill adopting a legacy id).
  Prerequisites now name their target explicitly via `toSkillId`/`toTempId`
  instead of relying on fuzzy description matching.
- `_consolidate_incremental.py` — **use this, not `_consolidate_chembook1.py`**,
  for any future batch. The older script rebuilds `tuples.json` from scratch out
  of the candidate files, which would re-mint every id and break the ids
  `prereqs.json` already references. This one merges a batch into the existing
  output, allocates ids that collide with neither the rebuild nor the legacy
  ontology, adopts legacy ids, and re-checks `unresolved_prereqs.json` against
  the newly added skills.
- `_find_near_dupes_b05b06.py` — the near-duplicate detector extended to compare
  new candidates against the consolidated rebuild and the legacy Chemistry set,
  not just against each other.
- `source_issues.json` — 3 records where the source book's own answer key or
  worked solution is wrong or self-contradictory (see `HANDOFF4.md` §4).

## What's NOT done yet

- `ChemBook2.txt` (957 records) — 0%.
- `MathBook1.txt` (802), `MathBook2.txt` (605) — Mathematics entirely unprocessed.
- `PhyBook1.txt` (615), `PhyBook2.txt` (764) — Physics entirely unprocessed.
- Cross-subject prerequisite resolution — still impossible until Mathematics and
  Physics have content. Several of the 46 remaining unresolved mentions are
  waiting on exactly this.
- The exhaustive legacy-id reuse check across *all* Chemistry topics. Widened
  this batch (all 117 legacy Chemistry skills were scanned by
  `_find_near_dupes_b05b06.py`, and the kinetics/equilibrium/thermochemistry
  topics were additionally read by hand), but still not a full pairwise diff.
- The independent quality-audit pass — never reached.
- The editorial decision on the 3 proposed new topics (unchanged this batch).
