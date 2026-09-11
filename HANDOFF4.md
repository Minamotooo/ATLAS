# ATLAS — Handoff 4: Full-Corpus Ontology Rebuild, `ChemBook1` complete

Continues `HANDOFF3.md`. **Read that first** — it holds the why, the project
owner's standing instructions, the cost-blowout lesson, and the consolidation
judgement rules, all of which are still in force and are not repeated here.
This document records what the b05+b06 batch did, the decisions made in it, and
where to pick up.

**One-line state:** `ChemBook1.txt` is now fully processed (731/731 records);
the rebuild holds **514 skills / 199 prerequisite edges**, validated as a DAG.
That is **16.3% of the 4,474-record corpus**. Everything else is unchanged.

---

## 1. What was done

Records 481–731 of `ChemBook1.txt` — the range `HANDOFF3.md` §7 named as step 1.
Content is almost entirely chemical equilibrium, acid–base/buffers/pH, chemical
kinetics, and thermochemistry, plus a short applied-chemistry tail (food
preservatives, fertilizers, consumer products).

| | before | after |
|---|---|---|
| Records processed | 480 | **731** (of `ChemBook1`'s 731) |
| Skills | 388 | **514** |
| Prereq edges | 109 | **199** (196 after transitive reduction) |
| Unresolved prereq mentions | 50 | **46** |
| Legacy ids reused | 4 | **10** |
| Max DAG depth | 3 | **4** |

Full per-file detail is in `Ontology/full_corpus_rebuild/STATUS.md`.

## 2. How it was done — the method that worked, repeat it

`HANDOFF3.md` §5 recommended: bigger chunks, ruleset inlined rather than
"go read these files", no wide parallel bursts, and consolidation done directly
rather than by an agent. **This batch went further and used no subagents at
all** — extraction included — and it worked well. Concretely:

1. **Dump the records to read.** A small script pulled the target range out of
   `parsed_items.jsonl` into two plain-text chunk files (question, options,
   answer, solution; `embed_text` dropped as redundant). ~120K characters for
   251 records. Do **not** re-parse the corpus — `parsed_items.jsonl` is correct
   and complete.
2. **Load the reuse references into context first, once.** A compact
   `skillId [Bloom] description` listing of all existing rebuild skills grouped
   by topic (~69K chars), plus the same for the 117 legacy Chemistry skills
   (~14K chars). This is the mechanism that makes the reuse rule enforceable —
   §3 of the system prompt is right that you cannot check reuse against a file
   you have not read.
3. **Read the records and extract**, writing a candidate JSON per chunk.
4. **Run `_find_near_dupes_b05b06.py`**, then judge every flagged pair by hand
   against `HANDOFF3.md` §6's rules.
5. **Run `_consolidate_incremental.py`.**
6. **Run `build_from_ontology.py --report-only`** and an integrity sweep.

Rough cost: reading 251 records plus the reference material dominates. This is
far cheaper than the original ~45-subagent workflow and produced a validated
result in one pass.

### Two tooling changes you should keep using

- **`_consolidate_incremental.py` replaces `_consolidate_chembook1.py` for all
  future batches.** The old script rebuilds `tuples.json` from scratch from the
  candidate files. Running it now would re-mint every skillId and silently
  invalidate every id `prereqs.json` already references. The new script merges a
  batch into the existing output, keeps existing ids stable, allocates new ids
  that collide with neither the rebuild nor the legacy ontology, adopts legacy
  ids, and re-checks `unresolved_prereqs.json` against the batch's new skills.
  Keep `_consolidate_chembook1.py` only as the historical record of how b01–b04
  were built.
- **Pin prerequisite targets explicitly.** Candidate `prereqs` entries now
  support `toSkillId` (an already-consolidated skill) and `toTempId` (a skill
  minted anywhere in the same batch) alongside the old `toDescription`. Fuzzy
  description matching at the 0.60 Jaccard threshold turned out to **miss real
  edges** — genuine matches were scoring 0.50–0.58 (see §3). Pinning all 48 of
  this batch's prerequisites raised the new-edge count from 70 to 86. Prefer
  pinning; leave `toDescription` as the fallback for a dependency that genuinely
  is not in the ontology yet.

The candidate schema also gained `reusedExistingSkills` and `reusedBatchSkills`.
These matter: when a record exercises a skill that already exists, the correct
output is **not** a new skill and **not** silence — it is a reuse entry, so the
skill's `sourceItemIds` grow and the provenance stays honest. 75 such references
were recorded this batch.

## 3. The fuzzy-matching threshold is too strict — known, partially handled

The 0.60 Jaccard auto-accept threshold inherited from `_consolidate_chembook1.py`
rejects true prerequisite matches whose wording differs in verbosity. Reviewing
the 0.50–0.60 band by hand found **11 of 12 flagged pairs were genuine matches**,
e.g.

- *"Define the rate of a chemical reaction as the change in concentration per
  unit time"* vs. *"…as the decrease in a reactant's concentration, or the
  increase in a product's concentration, per unit time"* — scored 0.58.
- *"Convert a given mass of a substance to moles using its molar mass"* vs.
  *"Calculate the number of moles of a substance from a given mass and its molar
  mass"* — scored 0.57.

**Do not simply lower the threshold**: the one false positive in that band
(*"periodic trend in ionic radius"* matching the *electronegativity* trend
skill at 0.50) shows why. The band needs eyes, not a looser number.

Four of those were resolved into `_consolidate_incremental.py`'s
`MANUAL_RESOLUTIONS` list, which is the right place for reviewed, pre-existing
dangling prerequisites. One of them (`CHE_BONDING44`) is a deliberate override
that points somewhere other than the top fuzzy hit. **When you process the next
batch, re-run the 0.50–0.60 review** over whatever remains in
`unresolved_prereqs.json` — this is cheap and recovers real edges.

## 4. Judgement calls made this batch (extends `HANDOFF3.md` §6)

Decisions worth keeping consistent next time:

- **Converse-direction pairs, kept separate** where the reverse direction needs a
  different operation: Arrhenius solved for `Ea` (needs a logarithm) vs. solved
  for the rate-constant ratio (needs an exponential); buffer pH from a known
  composition vs. the salt:acid ratio needed for a *target* pH (needs an
  antilogarithm). Consistent with §6's first-order-kinetics precedent.
- **`[H+]` from pH vs. pH from `[H+]` — kept separate, but it is a borderline
  call.** By §6's "trivial single-equation rearrangement" test these arguably
  merge (log and antilog are symmetric inverses, unlike the extra-step cases
  above). They were kept apart because the antilog direction is a genuine
  prerequisite of three other skills in this batch, so it needs to exist as a
  node. Flagging it explicitly so a later reviewer can overturn it deliberately
  rather than by accident.
- **Two different Hess's-law relations, kept separate**: `ΔH` from *formation*
  enthalpies (products − reactants) and `ΔH` from *combustion* enthalpies
  (reactants − products). Same shape, opposite sign convention, and confusing
  them is a classic student error — they are genuinely different procedures.
- **Same relation across topics → one skill, reused.** `k = 0.693/t½` is shared
  by first-order kinetics and radioactive decay; it was minted once under
  `CHEM_KIN` and reused from the `CHEM_NUCLEAR` dating skill. Cross-topic reuse
  is exactly what the reuse rule wants; do not mint a second copy per topic.
- **Merged**: a proposed "promoter used in the Haber process" skill was folded
  into the existing `CHEM_CAT3` (the Haber catalyst). Minting a Haber-specific
  promoter skill beside a Haber-specific catalyst skill is per-record minting,
  and legacy `CHEM_CAT1` already covers the general role of a promoter.
- **Widened two descriptions rather than minting near-duplicates** once later
  records showed them too narrow: the strong-acid/strong-base ionization skill
  now covers both acids and bases, and the Arrhenius-plot skill covers both the
  `log k` (slope `= -Ea/2.303R`) and `ln k` (slope `= -Ea/R`) forms. Widening an
  existing candidate is usually better than a second near-identical skill.

### Source-data errors found (`source_issues.json`)

Three records where the book itself is wrong or self-contradictory. Per Global
Constraint 5 (technical accuracy), the extracted skills state the correct
chemistry, not the book's answer:

- `ChemBook1__p86__q123__700` — the answer key says a bomb calorimeter holds
  *temperature* constant. It is a constant-**volume** device. The skill states
  the correct fact.
- `ChemBook1__p81__q83__660` — the book itself notes no option matches a correct
  reading of "the rate constant increases threefold", then back-solves to fit an
  option.
- `ChemBook1__p77__q43__620` — arithmetic typos in the worked solution
  (`(0.05)²` for `(0.65)²`, `0.1829` for `1.829`); the intended skill is
  unambiguous.

Expect more of these. Extract the skill, record the discrepancy, do not
propagate the error.

## 5. Exact next steps

Steps 1 of `HANDOFF3.md` §7 is now done. The rest carries over, renumbered:

1. **`ChemBook2.txt` — 957 records, 0% done.** These are absolute lines
   **732–1688** of `parsed_items.jsonl` (verified: line 732 is the first
   `ChemBook2.txt` record, line 1688 the last, line 1689 begins `MathBook1.txt`).
   Suggest 3 chunks of ~320. Finishing this completes Chemistry and is the
   natural next unit of work.
2. **Once all Chemistry is done**: re-run the legacy-id reuse check across *all*
   Chemistry topics (not just the high-overlap ones), then re-run
   `build_from_ontology.py --report-only`.
3. **`MathBook1.txt` (802) and `MathBook2.txt` (605)** — Mathematics entirely
   unprocessed. This unblocks the cross-subject prerequisites that several of
   the 46 unresolved mentions are waiting on.
4. **`PhyBook1.txt` (615) and `PhyBook2.txt` (764)** — Physics entirely
   unprocessed. **Watch for LaTeX-backslash corruption here** — this batch has
   none (formulas were written in plain text: `sqrt`, `delta`, `^`), but
   Physics/Maths content is far more formula-dense. Keep writing descriptions in
   plain text and the hazard stays avoided entirely.
5. **Cross-subject prerequisite resolution** once all three subjects exist.
6. **Quality audit** — an independent fresh-eyes pass. Still never reached; worth
   doing once there is enough combined content to sample meaningfully.
7. **Decide the 3 proposed new topics** (`new_topics_proposed.json`:
   `CHEM_LAB`, `CHEM_NUCLEAR`, `CHEM_DESCRIPTIVE`) in
   `Backend/tree_data/ontology_config.json`. Unchanged this batch — no new topics
   were proposed. This is a human editorial call and it is now blocking 53
   skills from ever appearing in the catalog (the build tool reports these three
   as "ingested but invisible").
8. **Decide how/whether this rebuild replaces the legacy ontology.** Still out of
   scope; legacy files remain untouched.

## 6. Ground rules that did not change

- The legacy ontology (`Ontology/{tuples.json,prereqs.json,skill_ontology_dag.html}`
  and everything under `Backend/tree_data/`) is **read-only reference**. Nothing
  in it was modified this batch. Verify with `git status` before committing.
- Skills stay maximally granular, decomposed into atomic steps, with
  reuse-before-minting checked against *everything accumulated so far*.
- One Bloom level per skill, chosen by the skill's own action verb.
- Current Bloom spread across all 514: Remember 191, Apply 185, Understand 88,
  Analyze 40, Evaluate 9, Create 1. The thin Evaluate/Create tail is a fair
  reflection of an admission-exam corpus, not a defect to manufacture entries
  for — but it is worth a look during the eventual quality audit.
