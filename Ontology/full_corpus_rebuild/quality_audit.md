# Quality Audit — Chemistry Rebuild (843 skills)

Date: 2026-09-18. Scope: all 843 skills in this directory's `tuples.json`,
compared against the 117 legacy Chemistry skills in `Ontology/tuples.json`.
This is the audit called for in `HANDOFF4.md` §7 item 4.

Method is mechanical and reproducible — description length, leading-verb vs
assigned Bloom level, cross-tier action detection, Jaccard near-duplicates. No
LLM calls. Every number below can be re-derived from the two `tuples.json` files.

> **Revision note (same day).** The first version of this audit reported "173
> multi-action skills (20.5%), `CHE_ORGANIC` 35.7%". **Those numbers were wrong
> and have been withdrawn.** They came from a regex that counted list items and
> elaborating clauses as separate actions — "Recall the catalyst, optimum
> temperature range, and pressure conditions" was scored as three actions when it
> is one. Hand review of all 173 flagged items found well over half were false
> positives. Finding 1 below now uses a criterion that cannot be fudged, and the
> numbers are much smaller. The original 173-item list is kept as
> `_multiaction_candidates.txt` for reference, but it is a *candidate* list, not
> a defect list.

---

## Headline: the suspected problem is not the actual problem

`HANDOFF4.md` §7 flagged `CHE_ORGANIC` (154 skills, the largest topic) as the
likely granularity drifter. **That hypothesis does not hold on the axis it named.**

| | CHE_ORGANIC | Rebuild (all 843) | Legacy Chemistry (117) |
|---|---|---|---|
| Median description length | 24 words | **25 words** | **13 words** |
| Skills spanning two Bloom tiers | 14 (9.1%) | **47 (5.6%)** | **1 (0.9%)** |
| Leading-verb ≠ Bloom *(now fixed)* | 18 | 68 | — |
| Near-duplicate pairs (Jaccard ≥ 0.55) | **1** | — | — |

`CHE_ORGANIC` is **exactly average** on description length — it did not drift
there. It is somewhat elevated on cross-tier bundling (9.1% vs 5.6%), but that is
a mild effect, not the outlier HANDOFF4 expected.

The larger finding is one HANDOFF4 did not anticipate: **the whole rebuild
drifted, not one topic.** At a 25-word median against legacy's 13, the rebuild is
~1.9× more verbose than the style the prompt explicitly told it to match ("match
the legacy ontology's grain, don't invent your own" —
`ontology_rebuild_system_prompt.md` Global Constraint 2). Stripping parenthetical
`(e.g., ...)` examples barely moves it (25 → 23), so this is real content, not
decoration.

---

## Finding 1 — 47 skills bundle two Bloom tiers into one node

**Criterion**, chosen to be unarguable: the description opens with a verb from one
Bloom row and coordinates (`and` / `, and` / `, then`) a second imperative verb
from a *different* Bloom row. The ontology's own rule is one Bloom level per
skill, so a skill spanning two tiers is by definition two skills.

**47 of 843 (5.6%)** in the rebuild, against **1 of 117 (0.9%)** in legacy — a 6×
rate increase. The full list is in `_cross_tier_skills.json`.

| Topic | Cross-tier | of | rate |
|---|---|---|---|
| `CHE_ORGANIC` | 14 | 154 | 9.1% |
| `CHE_ATOMIC` | 5 | 62 | 8.1% |
| `CHEM_REDOX` | 4 | 40 | 10.0% |
| `CHEM_ENV` | 3 | 27 | 11.1% |
| `CHE_BIOMOLECULE` | 3 | 23 | 13.0% |

Examples, with the two tiers named:

```
CHEM_DESCRIPTIVE23   Remember/"Recall"   + Apply/"write"
  "Recall that water gas is produced by passing steam over red-hot coke,
   and write the equation."

CHEM_PERIODIC31      Remember/"Recall"   + Apply/"use"
  "Recall the periodic trend that electronegativity increases across a period
   ..., and use it to identify the most/least electronegative element in a set."

CHEM_ENV22           Remember/"Define"   + Apply/"write"
  "Define CFCs as the chloro-fluoro derivatives of methane and ethane, and write
   the structural formula of a named Freon ... using the CFC numbering rule."
```

**Why this matters to the engine, not just to style.** `MasteryUpdater` holds one
`P(learned)` per skill, and one Bloom level selects that skill's guess/slip
parameters. A node that is half Remember and half Apply cannot have correct
parameters for both halves, and a learner who can recall the fact but not write
the equation drives the scalar to a value describing neither. Splitting these is
a correctness fix.

**Not counted here** are same-tier compounds ("Define X and give an example"),
which are stylistically loose but harmless to the model, and the many
false-positive list constructions that the withdrawn 173 figure swept up.

## Finding 2 — 68 skills carried a Bloom level their own verb contradicted ✅ FIXED

8.1% of skills opened with a verb from a different Bloom row than the level they
were assigned, violating the prompt's stated hard rule.

**All 68 have been corrected** — see `_apply_bloom_fixes.py`, which carries the
per-skill decision table and is idempotent and re-runnable. Verified **68 → 0**.

Two kinds of correction were needed, decided per skill by reading the described
cognitive work:

- **36 level corrections** — the assigned level was genuinely wrong. *These change
  engine behaviour*, because Bloom selects the BKT guess/slip parameters. A
  Remember-tier skill mislabelled Analyze was being scored with `p_g=0.12,
  p_s=0.18` instead of `p_g=0.30, p_s=0.05`, so one correct answer moved mastery
  far more than the evidence justified.
- **37 wording corrections** — the level was right and the verb was imprecise
  (`Identify ... by counting` is Apply-level work described with a Remember-tier
  verb). Reworded per the prompt's rule, "the description is wrong — rewrite it,
  don't relabel the level". No engine effect; keeps the data self-consistent for
  future extraction batches.

(Five skills needed both.) Resulting Bloom distribution shift:

| | Remember | Understand | Apply | Analyze | Evaluate | Create |
|---|---|---|---|---|---|---|
| before | 290 | 137 | 352 | 51 | 11 | 2 |
| after | **300** | **130** | **356** | **45** | **10** | 2 |

Post-fix integrity re-verified: 843 skills, skillIds and topicKeys unchanged, 0
duplicate ids, 0 dangling prerequisite refs, 0 stale cached prerequisite
descriptions (3 were re-synced after the rewording), no backslashes, DAG still
valid at 348 raw / 345 reduced edges, max depth 4.

## Finding 3 — Reuse discipline held up well

This is the good news, and it's the thing the rebuild prompt cared most about
("a rebuild that mints a fresh id per record instead of per atomic-skill has
failed regardless of how correct each individual entry looks").

Across 154 `CHE_ORGANIC` skills there is exactly **one** near-duplicate pair at
Jaccard ≥ 0.55:

```
CHE_ORGANIC71  Write the multi-step reaction sequence to interconvert two named
               AROMATIC compounds (toluene→benzene, phenol→benzene, ...)
CHE_ORGANIC72  Write the multi-step reaction sequence to interconvert two named
               ALIPHATIC compounds (methanol→ethanol, ethene→methanol, ...)
```

That pair is **legitimate** — aromatic and aliphatic interconversion are distinct
skills that happen to share phrasing. No action needed. For a 154-skill topic
assembled across four separate batches, one false-positive pair is a strong
result and corroborates STATUS.md's falling mint-rate evidence.

## Finding 4 — A trivia tail worth pruning

12 of 154 `CHE_ORGANIC` skills are single-fact recall pinned to one named
instance, below the grain size the prompt defined:

```
CHE_ORGANIC10   Recall that vinegar is a 6-10% aqueous solution of ethanoic acid.
CHE_ORGANIC133  Recall that tetraethyl lead is added to petrol as an anti-knocking agent.
CHE_ORGANIC134  Recall that chloropicrin is the principal constituent of tear gas.
```

`CHEM_DESCRIPTIVE` and `CHEM_LAB` have the same texture throughout — expected,
given those topics are descriptive by nature. Defensible as exam-prep content;
the question is whether each deserves its own DAG node. Low priority.

---

## Recommendations, in priority order

1. ~~Fix the verb/Bloom mismatches~~ — **done**, 68 → 0.

2. **Split the 47 cross-tier skills** (Finding 1), listed in
   `_cross_tier_skills.json`. Mechanical to detect, needs chemistry judgement to
   split well — each becomes two skills with new ids, and `prereqs.json` edges
   pointing at the original must be re-pointed at the correct half. This is the
   only remaining finding that affects the model rather than the metadata.

3. **Decide whether the global length drift is acceptable** (Headline). The
   rebuild is ~1.9× legacy's grain. It is internally *consistent* at that size, so
   this may be fine — but it should be a deliberate decision, because if the
   rebuild replaces the legacy ontology the two grains cannot coexist in one DAG.
   Whatever is decided should be written into the extraction prompt before
   Mathematics and Physics are processed, or the same drift repeats at 3× scale.

4. **Leave the near-duplicates alone** (Finding 3). Nothing to fix.

5. **Revisit the trivia tail** (Finding 4) during the `CHEM_DESCRIPTIVE` review
   already scheduled in STATUS.md.

## What this audit did not cover

- **Technical correctness of chemistry content** — no claim is made that any
  description is chemically accurate. This audit is structural only. A domain
  expert still needs to sample, and that includes sanity-checking the 68 Bloom
  decisions applied above.
- **Prerequisite edge correctness** — whether the 348 asserted edges are real
  logical dependencies. Not checked. Note separately that 373 skills (44.2%) have
  no edge at all, which is its own problem (see `Ontology/viz/README.md`).
- **Coverage** — whether the 1,688 source records yielded the right skills, or
  missed some.
