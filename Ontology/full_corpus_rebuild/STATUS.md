# Full-Corpus Ontology Rebuild — Status

**State: CORPUS COMPLETE AND EDITORIALLY CLOSED.** All 4,474 records of all six
source files are extracted, and the full pre-adoption editorial pass is done:
topic retagging, foundational skills, cross-tier splits, deduplication and a
structural validation sweep. `_validate_ontology.py` reports **zero errors**.
The only thing deliberately NOT done is adoption - see "Adoption" below.

| | skills | edges | edges/skill | isolated | topics |
|---|---|---|---|---|---|
| Chemistry | 886 | 868 | 0.97 | **0** | 59 |
| Mathematics | 446 | 499 | 1.10 | **0** | 52 |
| Physics | 356 | 376 | 1.06 | **0** | 72 |
| **total** | **1,688** | **1,743** | **1.03** | **0** | **183 / 183** |

Valid DAG, no cycle, max depth 9, **87 components (largest 482)**, 190 roots.
Every one of the 183 syllabus topics now holds at least one skill.

## What the pre-adoption pass changed

| | before | after |
|---|---|---|
| Syllabus topics with no skills | 54 | **0** |
| Unresolved prerequisite mentions | 46 | **0** |
| Isolated skills | 6 | **0** |
| Topics with no internal learning order | 5 | **0** |
| Topics holding a single skill | 4 | **0** |
| Duplicates | Math/Physics never checked | **0 after 7 merges** |
| Skills fusing two Bloom tiers | 47 flagged | **20 split, 27 rejected on review** |
| Max DAG depth | 7 | **9** |
| Largest connected component | 203 | **482** |
| Connected components | 187 | **87** |
| Near-orphan fragments (2-6 skills) | 91 | **32** |
| Skills | 1,624 | 1,688 |

Five scripts carry the work. Each holds its decision table in the file, so the
judgement is auditable rather than buried in a diff:

- **`_retag_topics.py`** - the big one. `topic_aliases` is a code-to-code map, so
  one old code collapsed onto exactly one syllabus code while its siblings sat
  empty: all 154 organic skills landed in "Hydrocarbons" while alcohols,
  carbonyls, amines and five other topics reported zero. 1,051 skills were
  re-filed by hand across 20 chapters. The run also absorbs the alias layer
  entirely - every skill in `tuples.json` now carries a syllabus code directly,
  and `topic_aliases` is a no-op for the rebuild.
- **`_author_foundations.py`** - 40 skills the corpus never taught. Three topics
  had no exercises anywhere in the six books (`MAT2_EXPONENTIAL_EQ`,
  `PHY1_ERRORS`, `PHY1_SOLID_BONDING`), and most of the 46 unresolved
  prerequisites named the same assumed knowledge - "solve a linear equation",
  "evaluate a logarithm", "calculate a molar mass", "balance an equation". HSC
  questions take these for granted; the DAG cannot. Authored skills carry
  `"authored": true` and no `sourceItemIds`, so they stay distinguishable from
  extracted ones.
- **`_split_cross_tier.py`** - 20 splits of skills that fused two Bloom tiers
  ("Recall X **and** write the equation for it"). 27 of the 47 candidates were
  rejected on reading: both halves at the same tier, or the second clause an
  example rather than a second action.
- **`_find_dupes_global.py`** / **`_merge_dupes.py`** - the first duplicate check
  ever run across the whole ontology rather than within one topic of one batch.
  7 merges, including three separate extractions of "recall the flame-test
  colour of a cation".
- **`_validator_fixes.py`** - what the structural sweep turned up: one edge left
  on the wrong half of a split, one wrong edge authored earlier in this same
  pass, a skill filed under organic nomenclature that was the definition of an
  ore, 4 isolated skills, 5 topics with no internal order, and 4 topics holding
  a single skill each.

### The fragment problem, and why it is only half fixed

`_edge_coverage.py` counts a skill as connected if it has **any** edge. That
flatters the graph: a pair of skills joined only to each other passes the gate
while forming an island of two. Under the conjunctive gate such an island is
barely different from an isolated node - nothing upstream gates it, and
mastering it pulls almost nothing up.

After the first editorial pass there were **91 such fragments holding 281
skills** - 17% of the ontology, all invisible to the coverage gate.
`_propose_fragment_links.py` proposed one edge per fragment mechanically. The
first scoring attempt, by token overlap, was ~40% usable: it kept proposing
lateral links between peers (zero-order kinetics "requiring" first-order
kinetics, the cosine rule "requiring" the sine rule) and returned one pair in
both directions, which would have closed a cycle. Re-scoring to prefer each
topic's **hub** - lowest Bloom tier, most dependents - rather than its nearest
sibling raised that to roughly two thirds.

All 83 proposals were then read. **48 were applied** (`_fragment_links.py`),
several of them reversed from what was proposed. **35 were rejected** and their
fragments deliberately left disconnected, because the proposal was backwards,
joined unrelated skills that merely share a chapter, or linked two peers that
need a common parent rather than each other.

Result: 136 components -> **87**, largest 415 -> **482**, fragments 91 -> **32**.

The remaining 32 are the clearest place where a chemist or physicist adds value
no heuristic can. Rerun `python _propose_fragment_links.py` to see them.

### A check that was wrong, and was withdrawn

`_validate_ontology.py` first flagged **147 "Bloom inversions"** - edges whose
prerequisite sits at a higher Bloom tier than the skill needing it - as errors.
Reading them showed the check, not the data, was wrong:

    MAT_MATRIX16 (Remember: a determinant with two equal rows is zero)
        requires MAT_MATRIX13 (Apply: evaluate a 3x3 determinant)

which is the correct order. Bloom tier measures cognitive demand, not teaching
sequence, and a low-tier *fact about* an operation is routinely learned after
the operation itself. Of the 147, hand-review found **3** genuinely reversed.
The check is kept as a review list, downgraded from ERROR to WARN, with the
reasoning in its docstring. This is the second time a mechanical heuristic has
over-flagged on this project by roughly the same factor - see the revision note
at the top of `quality_audit.md`.

## Decisions taken, and why

**Cross-subject overlap is linked, not merged.** HSC teaches some skills twice:
Higher Math 2nd Paper's Dynamics chapter repeats Physics 1st Paper kinematics
almost word for word, and Physics uses the vector products taught in Higher Math
1st Paper. Merging would empty `MAT2_PLANE_MOTION` and `MAT2_PROJECTILE`, so
both nodes are kept, marked `crossSubjectEquivalent`, and joined by a
prerequisite edge pointing at whichever subject teaches it first - Physics for
kinematics and projectiles, Mathematics for vector algebra. The edge is what
makes it work: under the ancestor pull-up, a student who proves the skill in one
subject is credited for it in the other. A true merge needs a schema that lets
one skill sit in two topics, which `topicKey` cannot express; the marking is
there so that change can find them. This is why the validator still reports 4
exact duplicate descriptions - they are deliberate.

**Granularity: accepted at the current grain.** The rebuild sits at a median of
7 skills per topic against the legacy ontology's 3 (mean 9.2 against 3.7), with
128 of the 183 topics holding between 1 and 9 skills. That is the right size for
a diagnostic that tests one skill at a time and has to localise a gap within a
topic. Four topics exceed 40 - `CHE1_REDOX` (48), `CHE1_PERIODIC_TRENDS` (47),
`CHE1_ACID_BASE` (46) and `CHE1_COVALENT_BOND` (44). They are deliberately not
split, because the NCTB syllabus does not subdivide them and the taxonomy is
anchored to that syllabus. Splitting them is a **taxonomy** decision rather than
an extraction one, and belongs to whoever owns the syllabus mapping.

**Three topics are filled entirely by authored skills** (`MAT2_EXPONENTIAL_EQ`,
`PHY1_ERRORS`, `PHY1_SOLID_BONDING`), and four more were topped up from one
skill (`CHE2_METALLURGY`, `PHY1_FRICTION`, `PHY2_LOGIC_GATES`,
`PHY1_SHM_ENERGY`). No corpus question supports those skills, so the question
generator has nothing to draw on for them yet. That is a recorded limit, not an
oversight.

## Still outstanding

- **Domain-expert review.** Two populations still want a chemist and a
  physicist: the 352 hand-authored Chemistry backfill edges from the earlier
  sparsity fix - especially in the organic topics, where the graph is now deep
  enough that a wrong edge propagates far through the ancestor pull-up - and the
  51 skills authored in this pass. Nothing mechanical substitutes for this.
- **32 near-orphan fragments remain** (see above) - the highest-value target
  for a domain expert.
- **29 higher-tier skills still have no prerequisite** although their topic
  holds lower-tier skills (`_validate_ontology.py`, check E5). Each was looked
  at; these are the ones where no candidate parent was clearly right, and a
  guessed edge is worse than a missing one.
- **Adoption**, below.

## Adoption

`Backend/tree_data/*.json` has **not** been regenerated. The live app still runs
the legacy 430-skill catalog. To adopt:

    python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --out-dir Backend/tree_data --force

This changes what every student sees, so it stays a deliberate, separate step.

## Physics (`PhyBook1` b19-b22, `PhyBook2` b23-b27)

| Chunk | Records | Content | Skills | Edges/skill |
|---|---|---|---|---|
| b19-b22 | 615 | all of `PhyBook1` — 1st Paper: measurement, vectors, kinematics, Newtonian mechanics, work and energy, gravitation, matter, periodic motion, waves, ideal gas | 155 | >= 1.0 |
| b23 | 150 | thermodynamics (2nd Paper Ch1); static electricity (Ch2) | 41 | 1.02 |
| b24 | 150 | current electricity (Ch3) — resistance, circuits, cells, bridges | 23 | 1.00 |
| b25 | 150 | magnetic effect of current (Ch4); induction and AC (Ch5) | 31 | 1.06 |
| b26 | 150 | geometrical optics (Ch6); physical optics (Ch7) | 25 | 1.04 |
| b27 | 164 | modern physics (Ch8); atomic and nuclear (Ch9); semiconductors (Ch10); astronomy (Ch11) | 67 | **1.12** |

b24 mints the fewest skills per record of any Physics batch. That is the source
material, not under-extraction: the current-electricity block is dozens of
near-identical resistance-network and power-consumption exercises, and the reuse
rule folds them onto the same skills.

b27 mints the most, because the four chapters it covers are the four the corpus
had never touched before — every topic in it started empty. Astronomy in
particular had no content at all until this batch; it was the last Physics
section still reporting as disabled.

## What's actually in `tuples.json` / `prereqs.json` right now

Extracted from **all 4,474 records of all six books**. Chemistry came first
(`ChemBook1` b01-b06, `ChemBook2` b07-b09), then Mathematics (`MathBook1`
b10-b14, `MathBook2` b15-b18), then Physics (`PhyBook1` b19-b22, `PhyBook2`
b23-b27). The Chemistry-only table below is kept as the historical record of the
first nine chunks.

| | after b01–b04 | after b05–b06 | **now (b01–b09)** |
|---|---|---|---|
| Records processed | 480 | 731 | **1,688** |
| Skills | 388 | 514 | **843** |
| Prerequisite edges | 109 | 199 | **700** (691 after transitive reduction; 348 at extraction, backfilled 2026-09-18) |
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

`python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --report-only`

**Valid DAG, no cycle.** 1,624 skills, 1,535 raw edges (1,491 after transitive
reduction, 44 redundant dropped), 134 raw / 129 canonical topics, 268 roots, max
depth 7, 187 components (largest 203). All three subjects present.

Data-integrity sweep, clean: **no duplicate skillIds** (1,624 unique of 1,624),
**no dangling prerequisite references**, no self-edges, no duplicate edges, and
**no backslashes anywhere** in any skill description (the LaTeX-escaping hazard
from `HANDOFF2.md` section 2 stays avoided by writing every formula in plain
text - `sqrt`, `delta`, `^`).

Edge-coverage gate (`_edge_coverage.py`), run per subject: **PASS on all three.**
Chemistry 0.83 / 0.7% isolated, Mathematics 1.09 / 0%, Physics 1.05 / 0%.

Bloom spread across all 1,624: Apply 995, Remember 398, Understand 168,
Analyze 51, Evaluate 10, Create 2.

The "unknown topics" / "empty sections" warnings are **not** what they look like,
and an earlier version of this file called them wrong. 54 syllabus topics report
zero skills, but in 52 of those cases **the skills exist** - they are sitting
under a sibling topic in the same chapter, because `topic_aliases` maps each old
topic code onto exactly **one** syllabus code and the corpus needed it split
across several. Examples, all verified:

| Empty topic | Skills that belong to it | Where they actually are |
|---|---|---|
| `MAT1_DETERMINANT` | 17 | `MAT1_MATRIX_ALGEBRA` |
| `CHE2_ORG_ALCOHOL` (+7 more organic topics) | 27+ | `CHE2_ORG_HYDROCARBON` (154 skills) |
| `MAT1_TRIG_RATIOS` | - | `MAT1_COMPOUND_ANGLE` (36 skills) |
| `CHE2_ELECTROLYSIS` | 9 | scattered across `CHE1_REDOX`, `CHE2_GALVANIC` |
| `PHY1_FRICTION` | 3 | `PHY1_NEWTON_LAWS`, `MAT2_STATICS_FRICTION` |

This is a **retagging job, not an extraction job** - see "Topic retagging" under
"What's NOT done yet". `build_syllabus_config.py::SPLIT_CANDIDATES` already
documents 8 of the worst offenders; the real count is 20 chapters.

Only `che1_ch05_applied` looks like a genuine content gap.

### Legacy topic prefixes are safe

Adopting legacy skillIds brings legacy topic codes (`CHEM_GAS`, `CHEM_GASLAW`,
`CHEM_KINETICS`, `CHEM_ELECTROCHEM`) in with them. All four are already aliased
in `Backend/tree_data/ontology_config.json`, which is why the build tool reports
30 raw topics collapsing to 27 canonical ones. No stray topics were created.

## Tooling in this directory

**Run this after any change to the ontology:**

    python _validate_ontology.py        # exits non-zero on an ERROR-level finding

The pre-adoption editorial pass added six scripts. Each carries its decision
table inline and takes `--dry-run`; all of them refuse to write on a cycle, an
unknown skillId or an id collision. In the order they were run:

- `_retag_topics.py` - per-skill topic assignment; also absorbs `topic_aliases`.
- `_author_foundations.py` - the 40 assumed-knowledge skills.
- `_split_cross_tier.py` - the 20 two-tier splits, and the 27 rejections.
- `_find_dupes_global.py` - whole-ontology duplicate detection (read-only).
- `_merge_dupes.py` - the 8 merges and the 10 cross-subject links. Re-runnable.
- `_propose_fragment_links.py` - proposes edges for near-orphan fragments
  (read-only); `_fragment_links.py` holds the 48 that survived review.
- `_validate_ontology.py` / `_validator_fixes.py` - the structural sweep and its
  fixes.

Backups from every pass are in `_prefix_backup/`: `tuples.pre_retag.json`,
`*.pre_foundations.json`, `*.pre_split.json`, `*.pre_merge.json`,
`*.pre_valfix.json`. Restore from these if a judgement is disputed.


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
- `_apply_bloom_fixes.py` — applies the 68 verb/Bloom corrections from
  `quality_audit.md` Finding 2. Idempotent and re-runnable; `--dry-run` first.
  The per-skill decision table is the file's whole point — read it before
  trusting the result. Originals in `_prefix_backup/`.
- `_prefix_backup/` — `tuples.json` / `prereqs.json` exactly as they were before
  the 2026-09-18 audit fixes. Restore from here if a correction is disputed.
- `_cross_tier_skills.json` — the 47 skillIds that bundle two Bloom tiers into
  one node (`quality_audit.md` Finding 1). The remaining work item.
- `_backfill_edges.py` — adds the prerequisite edges the extraction never
  proposed, one topic per batch. Its `EDGES` table is the deliverable: one
  hand-made judgement per skill, with the reasoning in comments. Refuses to write
  if an edge would close a cycle or name an unknown skillId; safe to re-run.
- `_edge_coverage.py` — measures prerequisite-edge coverage (edges per skill,
  percentage of skills with no edge) and **exits non-zero when below target**, so
  it can gate a batch merge. Run it after every batch. Current rebuild FAILs
  (0.41 / 44.2%); the legacy ontology PASSes (1.20 / 0%).
- `prereq_sparsity_diagnosis.md` — why the rebuild produced a sparse DAG, and the
  prompt changes made on 2026-09-18 to stop it recurring. Read before running
  Mathematics or Physics.
- `_multiaction_candidates.txt` — 173 regex-flagged candidates from the first
  audit pass. **A candidate list, not a defect list** — over half are false
  positives (see the revision note at the top of `quality_audit.md`). Kept only
  so the withdrawn number is traceable.

## What's NOT done yet

Extraction is finished. Everything below is editorial or review work.

- ~~`MathBook1.txt` / `MathBook2.txt`~~ - **DONE.** All 1,407 Mathematics records
  merged as b10-b18.
- ~~`PhyBook1.txt` / `PhyBook2.txt`~~ - **DONE (2026-09-18).** All 1,379 Physics
  records merged as b19-b27. `PhyBook2_b27` was the last batch of the corpus.
- ~~Prerequisite-edge backfill over the 843 Chemistry skills~~ - **DONE.** Root
  cause diagnosed and the extraction prompt fixed
  (`prereq_sparsity_diagnosis.md`); the existing skills were then backfilled in
  six batches via `_backfill_edges.py`. **Edges 348 -> 700, isolated skills
  44.2% -> 0.7% (6 left, all deliberate), edges/skill 0.41 -> 0.83, max DAG depth
  4 -> 6, largest component 44 -> 118.**
- **`Backend/tree_data/*.json` has still not been regenerated.** The live app is
  running on the old compiled catalog built from the legacy ontology. Adopting
  the rebuild is a separate, deliberate step:
  `python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --out-dir Backend/tree_data --force`.
  Do this only when you are ready for the live catalog to change.
- **Domain-expert review of the edges and the Bloom decisions.** Two populations
  need a human with the subject: the 352 hand-authored Chemistry backfill edges
  (especially `CHE_ORGANIC` - the graph is deep now, so a wrong edge propagates
  further through the ancestor pull-up), and the 68 Bloom corrections in
  `_apply_bloom_fixes.py`.
- **47 skills that bundle two Bloom tiers into one node**
  (`_cross_tier_skills.json`, `quality_audit.md` Finding 1). Each needs splitting
  into two skills with an edge between them.
- **8 cross-topic near-duplicate candidate pairs, plus 2 within-topic pairs**
  (`CHE_QUAL4`/`CHE_QUAL7`, `CHE_QUAL6`/`CHE_QUAL22`) need a human call. The
  `_find_near_dupes*.py` tools only ever compared within the same `topicKey`, so
  cross-topic duplicates were invisible for all nine Chemistry batches. List and
  caveats in `prereq_sparsity_diagnosis.md` under "Side finding". **The same
  check was never run at all for Mathematics or Physics** - worth doing now that
  both are complete.
- **Global granularity drift.** The rebuild sits at roughly 1.9x the legacy
  ontology's grain (1,624 skills vs 430 across a corpus the legacy set only
  sampled). That is a deliberate consequence of extracting the whole corpus, but
  it has not been signed off as the target grain.
- **Topic retagging - the biggest remaining job.** 54 syllabus topics report zero
  skills, but for 52 of them the skills exist and are mis-filed under a sibling
  topic (see the table under "Validation"). Cause: `topic_aliases` is a
  **code-to-code** map, so an old code like `CHE_ORGANIC` collapses onto exactly
  one syllabus code (`CHE2_ORG_HYDROCARBON`, now holding 154 skills) instead of
  fanning out across the nine organic topics the syllabus defines. **20 of the 51
  chapters are affected.** Worst offenders by size: `CHE2_ORG_HYDROCARBON` (154),
  `CHE1_ATOMIC_STRUCTURE` (62), `CHE1_ACID_BASE` (62), `CHE1_COVALENT_BOND` (54),
  `CHE2_GAS_LAWS` (50), `CHE1_REDOX` (40), `MAT1_LINE_EQUATION` (40),
  `CHE1_PERIODIC_TRENDS` (39), `MAT1_COMPOUND_ANGLE` (36).
  Fixing it needs a **per-skill** retag, not another alias: either add a
  `skill_topic_overrides` map to `ontology_config.json`, or rewrite `topicKey` in
  `tuples.json` directly. Until it is done the catalog shows students empty
  sections next to badly overloaded ones.
  `build_syllabus_config.py::SPLIT_CANDIDATES` documents 8 of these; the real
  count is 20.
- **`che1_ch05_applied` has no content at all** and may be a real gap in the
  source books. Decide whether to leave it disabled or source material for it.
- **46 unresolved prerequisite mentions** remain in `unresolved_prereqs.json`.
  Now that all three subjects have content, the cross-subject ones can finally be
  resolved - this was impossible while Chemistry stood alone.
- The exhaustive legacy-id reuse check across *all* topics. Much improved (all
  117 legacy Chemistry skills are scanned automatically every batch, and the
  gas-law, kinetics, thermochemistry and electrochemistry families were
  additionally read by hand, which is how 14 further legacy ids were picked up)
  but still not a full pairwise diff, and never done for Math or Physics.
- ~~The editorial decision on the 3 proposed new topics~~ - **DONE.** `CHEM_LAB`,
  `CHEM_NUCLEAR` and `CHEM_DESCRIPTIVE` were all accepted and added. See
  "Placement of the 3 accepted topics" below.
- ~~The independent quality-audit pass~~ - **DONE, see `quality_audit.md`.**
  Structural only; domain correctness still outstanding.

## Placement of the 3 accepted topics (2026-09-18)

All three proposals were accepted. They were placed into **existing** sections
rather than given new ones, so the live catalog stays at 20 enabled sections and
the running app is unchanged until the rebuild itself is adopted:

| Topic | Label | Skills | Section |
|---|---|---|---|
| `CHEM_NUCLEAR` | Nuclear Chemistry and Radioactivity | 18 | `chem_atomic_periodic` |
| `CHEM_LAB` | Laboratory Techniques and Safety | 16 | `chem_analytical_environmental` |
| `CHEM_DESCRIPTIVE` | Descriptive and Industrial Inorganic Chemistry | 24 | `chem_bonding` |

Verified against both ontologies with `--report-only`:

- **Rebuild source** — `catalog topics placed: 27`, no "ingested but invisible"
  warning. 843 skills, 345 reduced edges, max depth 4. Unchanged otherwise.
- **Legacy source** (`Backend/tree_data/ontology_source`) — still 430 skills, 66
  canonical topics, all 66 placed, max depth 7, 16 components. **No empty or
  disabled sections.** The build now prints one benign note that 3 sections
  reference topics the legacy ontology does not contain yet; that resolves itself
  when the rebuild lands.

`Backend/tree_data/*.json` was **not** regenerated — only `--report-only` was run,
so the live app's compiled catalog is byte-identical. Regenerating is a separate,
deliberate step.

### Caveat to revisit in the quality audit

`CHEM_DESCRIPTIVE` in `chem_bonding` is the weakest of the three placements — it
sits there because that section already holds `CHEM_DBLOCK` (Transition Elements)
and is the closest thing to an "elements and their compounds" grouping. The topic
is also the least coherent of the three on its own terms: 18 of its 24 skills are
Remember-tier recall of largely disconnected facts (alloy compositions, ore
sources, flame-test colours, water gas). Worth deciding during the quality audit
whether it should split, or earn a section of its own once the rebuild is adopted.

## Topic additions to `ontology_config.json` (2026-09-18)

Five topics were proposed by the rebuild and all five accepted. Each was placed
into an **existing** section, so the live catalog stays at 20 enabled sections
and the running app is unchanged until the rebuild itself is adopted.

| Topic | Label | Skills | Section | Raised by |
|---|---|---|---|---|
| `CHEM_NUCLEAR` | Nuclear Chemistry and Radioactivity | 18 | `chem_atomic_periodic` | Chemistry b01-b09 |
| `CHEM_LAB` | Laboratory Techniques and Safety | 16 | `chem_analytical_environmental` | Chemistry b01-b09 |
| `CHEM_DESCRIPTIVE` | Descriptive and Industrial Inorganic Chemistry | 24 | `chem_bonding` | Chemistry b01-b09 |
| `MAT_PERMCOMB` | Permutations and Combinations | 21 | `math_algebra` | `MathBook1_b11` |

Verified after each addition: the rebuild places every canonical topic with no
"ingested but invisible" warning, and the legacy build is byte-identical apart
from a benign note that some sections reference topics the legacy ontology does
not contain yet. `Backend/tree_data/*.json` has **not** been regenerated.

## Consolidator bug found and fixed (2026-09-18)

`_consolidate_incremental.py` allocated ids using

    re.match(r'^([A-Za-z_]+?)(\d+)$', skillId)

which **cannot match an id whose topic code itself contains a digit** — every
syllabus code does (`MAT1_DERIVATIVE0`, `PHY2_OHM3`, `CHE1_REDOX7`). Those ids
were therefore never registered as taken, `mint()` restarted at 0, and batch b14
minted `MAT1_DERIVATIVE0-3` and `MAT1_LIMIT0-1` on top of b13's skills of the
same name.

Two skills sharing an id merge into one graph node, which **fabricated a cycle**
(`MAT1_DERIVATIVE2 -> MAT1_DERIVATIVE0 -> MAT1_DERIVATIVE2`) and silently lost 6
skills and 2 edges. `build_from_ontology.py`'s cycle check is what caught it.

Fixed:

- the prefix pattern is now `^(.*[^0-9])(\d+)$` — everything up to the final run
  of digits, so digit-bearing topic codes parse correctly;
- the consolidator now **refuses to write** if any duplicate `skillId` survives
  minting, so this class of failure can never again land silently.

Recovery: `tuples.json` / `prereqs.json` were restored from the pre-b11 snapshot
and chunks b11, b12, b13, b14 were replayed in order with the fixed script.
Result verified: 1,124 skills, 1,016 edges, **no cycle, zero duplicate ids**,
0 dangling refs, max depth 7.

**This bug only bites batches using syllabus topic codes (b13 onward).** Chemistry
and the early Math batches were never affected.
