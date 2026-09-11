# ATLAS — Handoff 4: Full-Corpus Ontology Rebuild, all Chemistry complete

Continues `HANDOFF3.md`. **Read that first** — it holds the why, the project
owner's standing instructions, the cost-blowout lesson, and the consolidation
judgement rules, all still in force and not repeated here. This document records
what one working session did, the decisions made in it, and where to pick up.

**One-line state:** **all 1,688 Chemistry records are processed** —
`ChemBook1.txt` (731) and `ChemBook2.txt` (957). The rebuild holds **843 skills /
348 prerequisite edges**, validated as a DAG. That is **37.7% of the 4,474-record
corpus**. Mathematics and Physics remain untouched.

---

## 1. What was done

Five chunks, in order, each extracted → near-duplicate-checked → consolidated →
validated before the next was started:

| Chunk | Source range | Records | Minted | Reused |
|---|---|---|---|---|
| b05, b06 | `ChemBook1` 481–731 | 251 | 123 | 75 |
| b07 | `ChemBook2` 1–320 | 320 | 189 | 32 |
| b08 | `ChemBook2` 321–640 | 320 | 99 | 60 |
| b09 | `ChemBook2` 641–957 | 317 | 32 | 35 |

| | before | after |
|---|---|---|
| Records processed | 480 | **1,688** |
| Skills | 388 | **843** |
| Prereq edges | 109 | **348** (345 reduced) |
| Unresolved prereq mentions | 50 | **46** |
| Legacy ids reused | 4 | **24** |
| Topics (raw / canonical) | 25 / 25 | **30 / 27** |

Per-file detail is in `Ontology/full_corpus_rebuild/STATUS.md`.

The mint rate falls sharply across b07 → b08 → b09 (189 → 99 → 32). That is the
reuse rule working: b07 opened gas laws and organic chemistry from near zero,
b08's organic MCQs mostly re-exercised b07's skills, and by b09 only
electrochemistry was genuinely new. **A rising reuse ratio is the signal that the
ontology is converging; a flat mint rate late in a subject means reuse checking
has stopped working.**

## 2. The method — repeat this

`HANDOFF3.md` §5 recommended bigger chunks, an inlined ruleset, no wide parallel
bursts, and consolidation done directly. **This session used no subagents at all,
extraction included**, and it worked end to end. The loop, per chunk:

1. **Dump the records.** Pull the target range out of `parsed_items.jsonl` into a
   plain-text file (question, options, answer, solution; drop `embed_text`).
   Never re-parse the corpus — `parsed_items.jsonl` is correct and complete.
2. **Load the reuse references into context, once per session.** A compact
   `skillId [Bloom] description` listing of every existing rebuild skill grouped
   by topic, plus the same for the 117 legacy Chemistry skills. This is the
   mechanism that makes the reuse rule enforceable; you cannot check reuse
   against a file you have not read.
3. **Read the records and extract**, writing a candidate JSON per chunk.
4. **Run the near-duplicate detector**, then judge every flagged pair by hand
   against `HANDOFF3.md` §6.
5. **Run `_consolidate_incremental.py`.**
6. **Run `build_from_ontology.py --report-only`** plus an integrity sweep.

### Practical notes that cost time to learn

- **Bengali source text is byte-dense.** Roughly 200 lines of the dumped record
  files is all that fits in one tool call; slice accordingly.
- **Write candidate files in parts and assemble them with a script.** A single
  chunk can run to 190 skills, which is far too much for one file write. Write
  `candidates/parts/*.json` fragments, then assemble with a script that
  namespaces the tempIds and validates cross-references.
- **Validate every `skillId` you reference before consolidating.** The assembler
  checks reuse targets and prerequisite targets against the current ontology and
  the legacy set, and refuses to build if any is unknown. This caught several
  wrong ids. But note the limit: **an id existing does not mean it is the right
  one.** Spot-check the descriptions of ids you guessed — doing so caught
  `CHE_ATOMIC30` (isotopes/isobars) being wrongly used for a water-of-
  crystallisation record.

## 3. Tooling changes made this session

- **`_consolidate_incremental.py` replaces `_consolidate_chembook1.py`.** The old
  script rebuilds `tuples.json` from scratch out of the candidate files; running
  it today would re-mint every skillId and silently invalidate every id
  `prereqs.json` references. Keep it only as the record of how b01–b04 were built.
- **Prerequisite targets are pinned explicitly.** Candidate `prereqs` entries
  support `toSkillId` (an already-consolidated skill) and `toTempId` (a skill
  minted anywhere in the same batch) alongside `toDescription`. Fuzzy matching at
  the inherited 0.60 Jaccard threshold **misses real edges** — see §4.
- **`reusedExistingSkills` / `reusedBatchSkills`.** When a record exercises a
  skill that already exists, the correct output is neither a new skill nor
  silence: it is a reuse entry, so the skill's `sourceItemIds` grow and the
  provenance stays honest. 202 such references were recorded this session.
- **Legacy-id adoption.** If a batch reuses an id that exists only in the legacy
  ontology, the consolidator now copies that legacy entry (id, description,
  topic) into the rebuild rather than letting a near-duplicate be minted.
- **Fixed: `source_issues.json` was being overwritten** by each consolidation
  run instead of accumulated, so only the last batch's entries survived. The
  script now merges; the file was rebuilt from all nine candidate files and holds
  all 16 entries.

## 4. The fuzzy-match threshold is too strict — known, partially handled

The inherited 0.60 Jaccard auto-accept threshold rejects true prerequisite
matches whose wording differs only in verbosity. Reviewing the 0.50–0.60 band by
hand found **11 of 12 flagged pairs were genuine**, e.g. *"Convert a given mass
of a substance to moles using its molar mass"* vs. *"Calculate the number of
moles of a substance from a given mass and its molar mass"* — scored 0.57.

**Do not simply lower the threshold**: the one false positive in that band
(*"periodic trend in ionic radius"* matching the *electronegativity* trend skill
at 0.50) shows why. The band needs eyes, not a looser number. Four such pairs are
resolved in `_consolidate_incremental.py`'s `MANUAL_RESOLUTIONS`. Re-run that
review after each batch — it is cheap and recovers real edges. (Re-run at the end
of b09: nothing in the remaining 46 unresolved mentions now scores even 0.50, so
they are genuinely waiting on Math/Physics content.)

## 5. Judgement calls (extends `HANDOFF3.md` §6)

- **Converse-direction pairs, kept separate** where the reverse needs a different
  operation: Arrhenius solved for `Ea` (a logarithm) vs. for the rate-constant
  ratio (an exponential); buffer pH from a known composition vs. the salt:acid
  ratio for a *target* pH (an antilogarithm).
- **Converse-direction pairs, merged** where it is one rearrangement with no
  extra step: `PV = (m/M)RT` solved for mass vs. for molar mass; molarity from
  mass vs. mass from molarity. Consistent with §6's `Z + N = A` precedent.
- **`[H+]` from pH vs. pH from `[H+]` — kept separate, but it is borderline.** By
  the "trivial rearrangement" test these arguably merge. They were kept apart
  because the antilog direction is a genuine prerequisite of three other skills,
  so it must exist as a node. Flagged so a later reviewer can overturn it
  deliberately rather than by accident.
- **Two different Hess's-law relations, kept separate**: `ΔH` from *formation*
  enthalpies (products − reactants) and from *combustion* enthalpies (reactants −
  products). Same shape, opposite sign convention, classic student confusion.
- **Named laws kept separate from the general law they specialise.** Boyle's and
  Charles's laws were kept alongside the combined gas law, with prerequisite
  edges, because the corpus examines each by name and the edges capture the real
  teaching order.
- **Same relation across topics → one skill, reused.** `k = 0.693/t½` is shared by
  first-order kinetics and radioactive decay; minted once under `CHEM_KIN` and
  reused from `CHEM_NUCLEAR`. Do not mint a copy per topic.
- **A sub-route kept as its own skill.** "Limestone → ethyne" was kept separate
  from the longer "limestone → PVC" route, with the longer route depending on it.

### Source-data errors (`source_issues.json`, 16 entries)

Records where the book's own answer key or worked solution is wrong or
self-contradictory. Per Global Constraint 5 the extracted skills state the
correct chemistry, not the book's answer. Examples: a bomb calorimeter described
as constant-*temperature* (it is constant-*volume*); the Friedel-Crafts acylation
of benzene keyed as giving toluene (it gives acetophenone); burning more carbon
fuel keyed as causing ozone-layer holes (it causes warming). **Expect more.
Extract the skill, record the discrepancy, do not propagate the error.**

## 6. A real cycle was caught — trust the validator

While wiring the limestone→ethyne dependency, `build_from_ontology.py` failed
with `FAILED: prerequisite graph contains a cycle` on a two-node loop, because
the same dependency had been recorded in the opposite direction earlier in the
batch. The reverse edge was removed and validation passed.

This is the single cheapest correctness check available and it earns its keep.
**Run it after every consolidation, and read its exit code** — it returns 1 on a
cycle.

## 7. Exact next steps

Steps 1–3 of `HANDOFF3.md` §7 are now done. The rest, renumbered:

1. **`MathBook1.txt` (802) and `MathBook2.txt` (605)** — Mathematics entirely
   unprocessed, and the natural next unit. `MathBook1` begins at
   `parsed_items.jsonl` line **1689** (verified: line 1688 is the last
   `ChemBook2` record). Suggest chunks of ~300. Doing Mathematics first unblocks
   the cross-subject prerequisites that Chemistry is already waiting on.
2. **`PhyBook1.txt` (615) and `PhyBook2.txt` (764)** — Physics, entirely
   unprocessed.
   **Watch for LaTeX-backslash corruption in both subjects.** There is none in
   the ontology today because every formula is written in plain text (`sqrt`,
   `delta`, `^`). Maths and Physics are far more formula-dense; keep writing
   descriptions in plain text and the hazard stays avoided entirely.
3. **Cross-subject prerequisite resolution**, once all three subjects exist. The
   46 unresolved Chemistry mentions are the first input to this.
4. **Quality audit** — an independent fresh-eyes pass. Never reached, and now
   overdue: Chemistry is complete enough to sample meaningfully. Worth checking
   in particular whether `CHE_ORGANIC` (154 skills, by far the largest topic) has
   drifted in granularity relative to the rest.
5. **Decide the 3 proposed new topics** (`CHEM_LAB`, `CHEM_NUCLEAR`,
   `CHEM_DESCRIPTIVE`) in `Backend/tree_data/ontology_config.json`. Unchanged
   this session — no new topics were proposed in b07–b09 — but it now blocks
   **58 skills** from ever appearing in the catalog, which the build tool reports
   as "ingested but invisible". This is a human editorial call.
6. **Decide how/whether this rebuild replaces the legacy ontology.** Still out of
   scope; the legacy files remain untouched.

## 8. Ground rules that did not change

- The legacy ontology (`Ontology/{tuples.json,prereqs.json,skill_ontology_dag.html}`
  and everything under `Backend/tree_data/`) is **read-only reference**. Nothing
  in it was modified. Verify with `git status` before committing.
- Skills stay maximally granular, decomposed into atomic steps, with
  reuse-before-minting checked against everything accumulated so far.
- One Bloom level per skill, chosen by the skill's own action verb.
- Current spread across 843: Apply 352, Remember 290, Understand 137, Analyze 51,
  Evaluate 11, Create 2. The thin Evaluate/Create tail reflects an
  admission-exam corpus rather than a defect — but it is worth a look during the
  quality audit rather than manufacturing entries to pad it.
