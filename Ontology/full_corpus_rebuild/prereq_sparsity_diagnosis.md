# Why the rebuild produced a sparse DAG — diagnosis and prompt fix

Date: 2026-09-18. Companion to `quality_audit.md`, which flagged the symptom but
scoped the cause out.

**Symptom.** 843 Chemistry skills, 348 prerequisite edges. **373 skills (44.2%)
have no edge in either direction**; the connected remainder breaks into 126
fragments, largest 44. Those 373 are inert: `MasteryUpdater` reads `parent_ids`
for its conjunctive gate and ancestor pull-up, so a skill with no parents is never
gated and a skill with no children never propagates evidence.

---

## The measurement that frames everything

| ontology | skills | edges | edges/skill | no edge |
|---|---|---|---|---|
| **Legacy** (all subjects) | 430 | 515 | **1.20** | **0 (0%)** |
| **Legacy** (Chemistry only) | 117 | 140 | **1.20** | **0 (0%)** |
| **Rebuild** (Chemistry) | 843 | 348 | **0.41** | **373 (44.2%)** |

The legacy ontology — built with the *older, simpler, ad-hoc chat prompts* in
`Work done already.md` — is three times denser and has no isolated skills at all.
The elaborate, carefully-engineered rebuild prompt produced a worse DAG than the
casual one it replaced. That inversion is the thing to explain.

## Not the consolidator

Checked first, and cleared. Across the nine candidate files the extraction
proposed **397 edges**; 348 survived into `prereqs.json` and 45 are logged in
`unresolved_prereqs.json`. Nothing meaningful was dropped in the merge — the
consolidator faithfully preserved what it was given. **The extraction only ever
produced ~0.47 edges per skill**, and it did so uniformly:

| batch | new skills | edges proposed | edges/skill |
|---|---|---|---|
| ChemBook1_b01 | 95 | 42 | 0.44 |
| ChemBook1_b02 | 81 | 36 | 0.44 |
| ChemBook1_b03 | 86 | 36 | 0.42 |
| ChemBook1_b04 | 140 | 48 | 0.34 |
| ChemBook1_b05 | 75 | 53 | 0.71 |
| ChemBook1_b06 | 48 | 33 | 0.69 |
| ChemBook2_b07 | 189 | 65 | 0.34 |
| ChemBook2_b08 | 99 | 56 | 0.57 |
| ChemBook2_b09 | 32 | 28 | 0.88 |

Flat across all nine. Not degradation, not context exhaustion, not a bad batch —
a constant rate. A constant rate means a structural cause in the instructions.

## The cause: prerequisites were framed as a within-record question

Four compounding defects in `ontology_rebuild_actual_prompt.md`, all now fixed.

**1. The question asked was structurally unanswerable.** Step 3 asked, per record,
whether a skill depends on another skill — with the worked example concluding
"nothing in *this record* depends on anything else *in it*." But the corpus yields
a mean of **1.24 skills per source record**. Most records produce exactly one
skill, so a within-record dependency check can only return "no". Prerequisite
structure is inherently cross-record: a record testing redox balancing does not
contain the oxidation-number skill it presupposes — that was extracted hundreds of
records earlier.

The model was not ignoring the instruction. It was answering the question it was
asked, and that question had almost no "yes" available.

Evidence it *wanted* to reach further: of the 397 proposed edges, only 84 joined
two skills from the same source record. 131 spanned different records and 182
pointed at skills outside the current batch entirely. The model reached outward
wherever the framing let it — the framing just didn't let it often.

**2. The only worked example demonstrated emitting nothing.** The actual prompt's
single illustration of prerequisite handling ended in the null case. The reuse
rule, by contrast, got a worked example, a Global Constraint, and an explicit
failure definition.

**3. The Quality Checklist had seven items and none of them checked edges.** Every
other constraint — reuse, Bloom levels, topic discipline, LaTeX escaping, progress
accounting, legacy read-only — had an enforcement line. The one prerequisite item
checked that `depth` was formatted as `0`. Nothing checked whether edges existed.

**4. Nothing was reported per batch.** The tally line printed records, skills and
topics — not edges. A sparse run was therefore invisible for nine consecutive
batches.

## The fix

**`ontology_rebuild_system_prompt.md`** — new Global Constraint 4, "Prerequisite
density", placed beside the reuse rule and written with the same force, including
a parallel failure definition: *a rebuild whose skills are individually correct but
mutually unconnected has failed in exactly the same way as one that mints a fresh
id per record.* Constraints 4–7 renumbered to 5–8; the cross-references to
constraints 2 and 3 elsewhere are unaffected.

**`ontology_rebuild_actual_prompt.md`** — four changes:

- Step 3 rewritten to ask the accumulated-ontology question explicitly, and to
  name the within-record question as the thing that caused this failure.
- The worked example replaced with one emitting **three edges from two skills**,
  none of which come from inside the record — the point being made explicitly.
- Two new Quality Checklist items: edges ÷ new skills ≥ 1.0 (floor 0.8), and
  ≤ 25% of new skills with zero prerequisites.
- The per-batch tally and the end-of-session report now both carry edges-per-skill
  and isolated-percentage, with the Chemistry numbers quoted as the counter-example.

**`_edge_coverage.py`** — makes the checklist item checkable instead of
aspirational. Exits non-zero when either threshold is missed, so it can gate a
batch merge the way `build_from_ontology.py --report-only` gates the DAG.

```bash
python Ontology/full_corpus_rebuild/_edge_coverage.py --by-topic
```

Current: rebuild **FAIL** (0.41, 44.2%), legacy **PASS** (1.20, 0%). The 1.0
target is not invented — it is calibrated to what the legacy ontology already
achieves.

## The backfill, and where to start

The prompt fix stops the next batch reproducing this. It does nothing for the 843
skills already extracted, which need an edge-only pass. Worst topics first —
these are where the missing structure is concentrated:

| topic | skills | no edge | |
|---|---|---|---|
| `CHEM_DESCRIPTIVE` | 24 | 24 | 100% |
| `CHEM_SOLID` | 10 | 10 | 100% |
| `CHE_COORD` | 10 | 9 | 90% |
| `CHEM_LAB` | 16 | 14 | 88% |
| `CHE_QUAL` | 22 | 18 | 82% |
| `CHEM_DBLOCK` | 19 | 14 | 74% |
| `CHEM_ENV` | 27 | 19 | 70% |
| `CHEM_PERIODIC` | 39 | 26 | 67% |
| `CHE_ORGANIC` | 154 | 79 | 51% |

Note the shape of that list: the fully-isolated topics (`CHEM_DESCRIPTIVE`,
`CHEM_SOLID`, `CHEM_LAB`) are the descriptive/recall-heavy ones, where each skill
is a standalone fact. Some of that isolation is legitimate — but 100% is not, and
`CHEM_DESCRIPTIVE`'s skills clearly depend on `CHEM_PERIODIC` and `CHEM_REDOX`
content that already exists in the ontology.

The topics at the bottom (`CHE_ELECTROCHEM` 9%, `CHE_EQUILIBRIUM` 11%,
`CHEM_KIN` 14%, `CHE_STOICHIOMETRY` 16%) show the extraction *could* build dense
structure when the material had obvious internal dependencies. That is the standard
the rest should reach.

**Do the backfill before Mathematics and Physics**, not after. The same prompt run
over 2,786 more records would add roughly 1,400 more skills at the same 0.47 rate —
turning a 373-skill problem into a ~1,000-skill one.

---

## Backfill log

### Batch 1 — `CHEM_DESCRIPTIVE`, 2026-09-18

24 skills, previously **100% isolated**. Now **0% isolated** — every skill has at
least one edge. 29 edges added by `_backfill_edges.py` (its `EDGES` table carries
the reasoning for each, one comment per group).

| | before | after |
|---|---|---|
| Rebuild edges | 348 | **377** (372 after transitive reduction) |
| Skills with no edge | 373 (44.2%) | **341 (40.5%)** |
| `CHEM_DESCRIPTIVE` isolated | 24 (100%) | **0 (0%)** |

DAG re-validated: no cycle, max depth 4, 0 dangling refs, 0 stale cached
descriptions. The backfill script refuses to write if any edge would close a cycle
or reference an unknown skillId, and is safe to re-run.

Most edges reach **out of the topic** — into `CHEM_REDOX`, `CHEM_PERIODIC`,
`CHE_ACIDBASE`, `CHEM_SOLUTION`, `CHEM_SOLID` and `CHE_COORD`. That is the whole
point: `CHEM_DESCRIPTIVE` looked foundational only because it was being read one
record at a time. Against the accumulated ontology its dependencies are obvious —
"HF etches glass" needs "glass contains silica"; "alkali metals react vigorously
with water" needs the group classification and the reactivity series.

**Remaining worst topics**, for the next batches:

| topic | skills | no edge | |
|---|---|---|---|
| `CHEM_SOLID` | 10 | 9 | 90% |
| `CHEM_LAB` | 16 | 14 | 88% |
| `CHE_QUAL` | 22 | 18 | 82% |
| `CHEM_DBLOCK` | 19 | 14 | 74% |
| `CHEM_ENV` | 27 | 19 | 70% |
| `CHEM_PERIODIC` | 39 | 26 | 67% |
| `CHE_ORGANIC` | 154 | 79 | 51% |

### Side finding: duplicate detection never compared across topics

While sourcing prerequisites for `CHEM_DESCRIPTIVE` it became clear that
`CHEM_DESCRIPTIVE4` ("recall the characteristic flame-test colour of a metal ion")
duplicates `CHE_QUAL6` and `CHE_QUAL22`, which say the same thing in another topic.

The cause is in the tooling: `_find_near_dupes*.py` compares descriptions **only
within the same `topicKey`** (cheap, and it is documented that way in
`HANDOFF3.md`). Cross-topic duplicates were therefore structurally invisible for
all nine batches. A cross-topic sweep at Jaccard ≥ 0.45 finds **8 candidate pairs**:

```
0.54  CHEM_DESCRIPTIVE4   <-> CHE_QUAL22          flame-test colour of a metal ion
0.50  CHEM_DESCRIPTIVE1   <-> CHEM_NOM9           formula from trivial/commercial name
0.50  CHEM_DESCRIPTIVE2   <-> CHEM_DBLOCK16       alloy composition
0.50  CHEM_DESCRIPTIVE15  <-> CHEM_PERIODIC24     practical application of a noble gas
0.50  CHEM_ANALYTICAL15   <-> CHE_STOICHIOMETRY7  percentage of an element, gravimetric
0.50  CHEM_DBLOCK8        <-> CHEM_PERIODIC30     which elements are ferromagnetic
0.50  CHE_GASLAWS39       <-> CHE_STOICHIOMETRY19 volume of a single gas molecule at NTP
0.47  CHEM_SOLUTION9      <-> CHE_STOICH3         percentage concentration into molarity
```

These are **candidates, not confirmed duplicates** — some may be legitimately
distinct (the two gravimetric-percentage skills plausibly differ in method). They
need the same human judgement the within-topic pairs got.

> **Carry-over risk:** this batch used `CHEM_DESCRIPTIVE1` as the prerequisite for
> five skills. If `CHEM_DESCRIPTIVE1` and `CHEM_NOM9` are later merged, those five
> edges must be re-pointed at the surviving id.

### Batch 2 — `CHEM_SOLID`, `CHEM_LAB`, `CHE_QUAL`, 2026-09-18

48 skills, 41 previously isolated. 38 edges added.

| topic | skills | isolated before | isolated after |
|---|---|---|---|
| `CHEM_SOLID` | 10 | 9 (90%) | **1 (10%)** |
| `CHEM_LAB` | 16 | 14 (88%) | **2 (12%)** |
| `CHE_QUAL` | 22 | 18 (82%) | **2 (9%)** |

| | after batch 1 | after batch 2 |
|---|---|---|
| Rebuild edges | 377 | **415** (409 reduced) |
| Skills with no edge | 341 (40.5%) | **298 (35.3%)** |
| Largest component | 44 | **54** |

DAG re-validated: no cycle, max depth 4, 0 dangling refs, 0 stale descriptions.

As in batch 1, most edges leave their topic — `CHE_QUAL` leans on
`CHEM_SOLUTION7` (solubility rules), `CHE_COORD7` (ammine complexation) and
`CHE_EQUILIBRIUM10`/`15` (Ksp and partial dissociation); `CHEM_LAB` leans on
`CHEM_SOLID4`, `CHE_ORGANIC51`, `CHE_ACIDBASE6` and `CHE_BONDING31`. A topic
called "Laboratory Techniques" looks like disconnected trivia until you ask what
each fact presupposes.

**Five skills deliberately left isolated** — they are genuinely foundational or
are duplicates whose merge will resolve them:

| skill | why |
|---|---|
| `CHEM_SOLID2` | nanoparticle size range — standalone recall, nothing presupposes it |
| `CHEM_LAB2` | which liquid burns with a sootier flame — no honest prerequisite in the ontology |
| `CHEM_LAB14` | beam-balance rider calculation — a physics skill sitting in a chemistry topic |
| `CHE_QUAL6`, `CHE_QUAL22` | duplicate flame-test skills (see below); merging them is the fix, not an edge |

No edge was invented to hit a number. Where nothing in the accumulated ontology
genuinely precedes a skill, it stays a root.

### More duplicates, same cause

`CHE_QUAL4` and `CHE_QUAL7` both say "explain why a weak acid rather than a strong
acid is used before a qualitative precipitation test" — a **within-topic** pair
that `_find_near_dupes*.py` should have caught and did not, alongside
`CHE_QUAL6`/`CHE_QUAL22` (flame test). Both pairs are in `CHE_QUAL`, a topic whose
candidates were spread across batches b01–b09, which suggests the dupe check was
run per batch rather than against the accumulated set for that topic. Worth
confirming before the next subject is processed.

### Batches 3–6 — every remaining topic, 2026-09-18

Completed in four passes: batch 3 (`CHEM_CAT`, `CHE_COORD`, `CHEM_NOM`,
`CHEM_DBLOCK`, `CHEM_ENV`, and the `CHEM_GAS`/`CHEM_GASLAW`/`CHEM_KINETICS`
alias topics), batch 4 (`CHEM_PERIODIC`, `CHEM_SPEC`, `CHE_ATOMIC`,
`CHE_BONDING`), batch 5 (`CHEM_REDOX`, `CHEM_NUCLEAR`, `CHE_BIOMOLECULE`,
`CHEM_ANALYTICAL`, `CHEM_SOLUTION`, `CHE_ACIDBASE`, `CHE_GASLAWS`,
`CHE_THERMOCHEM`, `CHE_STOICHIOMETRY`, `CHEM_KIN`, `CHE_EQUILIBRIUM`,
`CHE_ELECTROCHEM`, `CHEM_STEREO`), batch 6 (`CHE_ORGANIC`, 78 skills).

## Backfill complete — final state

| | start | end |
|---|---|---|
| Prerequisite edges | 348 | **700** (691 after transitive reduction) |
| Edges per skill | 0.41 | **0.83** |
| Skills with no edge | 373 (44.2%) | **6 (0.7%)** |
| Root skills | 519 | **193** |
| Max DAG depth | 4 | **6** |
| Weakly-connected components | 499 | **154** |
| Largest component | 44 | **118** |

`_edge_coverage.py` now **PASSES** (exit 0) where it failed at the start. The DAG
validates with no cycle, 0 dangling references, 0 stale cached descriptions, and
843 skills / 27 canonical topics unchanged. Skill ids, topics, Bloom levels and
descriptions were never touched — this pass only added edges.

For comparison, the legacy ontology sits at 1.20 edges/skill with 0% isolated.
The rebuild is now in the same regime, though still below legacy density; the gap
is mostly that legacy had 430 skills over the same conceptual ground, so its
graph is naturally tighter.

### The six skills deliberately left isolated

| skill | why |
|---|---|
| `CHEM_SOLID2` | nanoparticle size range — standalone recall |
| `CHEM_LAB2` | which liquid burns sootier — no honest prerequisite exists |
| `CHEM_LAB14` | beam-balance rider calculation — a physics skill in a chemistry topic |
| `CHEM_NOM4` | full forms of abbreviations (FTIR, AAS, MRI) — pure vocabulary |
| `CHE_QUAL6`, `CHE_QUAL22` | duplicate flame-test skills; merging is the fix |

No edge was invented to improve a number. Where nothing in the ontology genuinely
precedes a skill, it stays a root.

### What this pass did not do

Every edge is a **structural** judgement — "does this skill presuppose that one?"
— made against skill descriptions, not against the chemistry literature. A domain
expert should sample them, particularly in `CHE_ORGANIC`, where the chains were
built from reaction-family logic (aromaticity → nitration → aniline; carboxylic
acid → acyl chloride → amide → Hofmann) rather than from the source records.

Depth 6 and a 118-skill largest component mean the conjunctive gate in
`MasteryUpdater` now has real structure to work with. It also means a wrong edge
now propagates further than it used to — the ancestor pull-up reaches further up
a deeper graph — so the expert sample matters more after this pass than before it.
