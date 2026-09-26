# 04 — Ontology editorial & QA pass

> **What this is.** The prompt for the cleanup that turns raw extraction output
> into a shippable ontology. Extraction gets you skills; this gets you a graph.
>
> **Why it exists.** After all 4,474 records were extracted the ontology looked
> finished — it validated, it had no cycles, the coverage gate passed. It was
> not finished. **54 of 183 topics held zero skills**, 46 prerequisite
> references pointed at nothing, and 17% of skills sat in 2–6-skill islands that
> the coverage gate counted as "connected". None of that is visible in a
> validator that only checks structure.
>
> **When it runs.** After extraction is complete, before the ontology is adopted
> or used for question generation.
>
> **What it produced.** 54 empty topics → 0 · 46 unresolved prerequisites → 0 ·
> 6 isolated skills → 0 · 91 near-orphan fragments → 32 · components 187 → 87 ·
> largest component 203 → 482 · DAG depth 7 → 9.
>
> **Status.** Reconstructed from the passes actually run. Each pass shipped as a
> script under `Ontology/full_corpus_rebuild/_*.py` carrying its decision table
> inline, which is the pattern this prompt asks you to follow.

---

## System framing

You are an ontology editor and validator. You did not build this ontology and
you are not defending it. Your job is to find what is wrong with it and fix only
what you can justify.

**The governing rule of this entire pass:**

> A wrong prerequisite edge is worse than a missing one.

A missing edge means the engine gates one skill less than it could. A wrong edge
propagates through the ancestor pull-up and silently corrupts mastery estimates
for everything downstream — and nothing in the system will ever flag it. When
you cannot justify an edge, leave it out and log it.

---

## Instruction

Run the passes below **in order** — each depends on the previous one's output.
For every pass:

- Write it as a **script with its decision table inline** in the source, not as
  a one-off edit. The table is the deliverable; the diff is not reviewable
  without it.
- Support `--dry-run`.
- **Refuse to write** on a cycle, an unknown skill id, or an id collision.
- Back up `tuples.json` / `prereqs.json` before writing.
- Make it idempotent — re-running changes nothing.

---

## Pass 1 — Topic retagging

**Find:** every syllabus topic holding zero skills. For each, check whether the
skills that belong to it exist but are filed elsewhere.

**Expect them to exist.** If topic assignment went through a code-to-code alias
map, one old code collapsed onto exactly one new code and its siblings were
starved. Verify before assuming a gap is a gap:

```
MAT1_DETERMINANT      0 skills → 17 determinant skills sitting in MAT1_MATRIX_ALGEBRA
CHE2_ORG_ALCOHOL      0 skills → 27 alcohol skills sitting in CHE2_ORG_HYDROCARBON (154 skills)
```

**Fix:** a **per-skill** retag table. An alias cannot fix this — the split is
per skill, not per code.

While you are here, **absorb the alias layer entirely**: write the resolved
syllabus code into every skill's `topicKey` so the data is self-describing and
the alias map becomes a no-op. A topic assignment that depends on a translation
layer is one indirection away from silently breaking again.

**Distinguish two cases and treat them differently:**
- *mis-filed* — the skills exist elsewhere → retag;
- *genuinely absent* — no skill in the corpus covers it → leave empty, record
  it, and handle it in Pass 2.

Verify by searching the corpus for the topic's subject matter before declaring
a gap. Getting this backwards means either inventing content that already
exists or leaving a real hole unfilled.

---

## Pass 2 — Author the foundations the corpus assumes

**Find:** topics still empty after Pass 1, and every unresolved prerequisite
reference.

**Expect these to be the same problem.** Textbooks do not set questions on
what they assume you already know, so the corpus contains no item teaching
*"solve a linear equation"*, *"evaluate a logarithm"*, or *"balance a chemical
equation"* — yet dozens of extracted skills depend on exactly those. The DAG
needs them as roots.

**Fix:** author them. Keep each one short, single-action, and genuinely
prerequisite to the skills that asked for it. Then wire the edges that resolve
the dangling references.

**Mark every authored skill** with a flag such as `"authored": true` and no
source item. Two reasons: they stay distinguishable from extracted skills
forever, and RAG-based question generation will retrieve nothing for them — so
whoever generates questions needs to know which ones will be weakly grounded.

---

## Pass 3 — Split skills that fuse two competencies

**Find:** descriptions joining two independently-testable actions —
*"Recall the definition of saponification **and write the equation** for it."*

**Why:** BKT keeps one `p_learned` per skill. Two competencies under one id
share a single mastery number, so a student who can do one but not the other is
scored as though those were the same thing, and the DAG cannot express that one
leads to the other.

**Expect your detector to over-flag by roughly half.** Reject, don't split,
when:
- both halves sit at the same cognitive tier — *"determine **and name** the
  shape"* is one skill in two words;
- the second clause is an example or gloss, not an action — *"define CFCs **and
  write the formula of a named Freon**"*;
- it is a genuine higher-tier task whose lower half is a *prerequisite* rather
  than a component — *"examine a set of configurations and identify the
  incorrect one"*. Those get an **edge**, not a split.

Read every candidate. Record the rejections and why — the rejection list is as
much a deliverable as the splits.

---

## Pass 4 — Deduplicate across the whole ontology

**Find:** near-duplicate skills. Compare **every pair in the ontology**, not
within a topic and not within a batch.

**Why the scope matters:** per-topic comparison cannot see the same skill
extracted into two different topics. *"Recall the flame-test colour of a
cation"* was extracted **three separate times** — twice in qualitative analysis,
once in descriptive chemistry — and no within-topic check could ever have found
it.

**Three findings, three different answers:**

1. **True duplicate** → merge. Keep one id, rewire the loser's edges onto the
   winner, delete the loser.
2. **Cross-subject overlap** → *do not merge.* Some skills are genuinely taught
   in two subjects (HSC Higher Maths Dynamics repeats Physics kinematics almost
   verbatim). Merging empties one subject's topic. Keep both, mark them
   equivalent, and join them with a prerequisite edge pointing at whichever
   subject teaches it first — the edge is what makes mastery propagate between
   them under the ancestor pull-up.
3. **Remember/Apply pair** → not duplicates. *"Recall that N = A − Z"* and
   *"Calculate the neutrons given A and Z"* are two skills that were merely
   missing the edge between them. Add it.

---

## Pass 5 — Structural validation

Build a validator that checks whether the graph is **sensible**, not merely
whether it loads. Report each finding separately, and be explicit about which
are errors and which are review lists.

Checks worth having:

| Check | Looks for |
|---|---|
| Isolated skills | no edge in either direction — inert under the conjunctive gate |
| Stale cached text | a cached parent description that has drifted from the skill's own |
| Topics with no internal edge | a topic with no learning order, only a label |
| Ungrounded higher-tier skills | Apply/Analyze with no prerequisite, in a topic that has lower-tier skills |
| Singleton topics | one skill — cannot localise anything |
| Exact duplicate descriptions | survivors of Pass 4 |
| Label drift | `topicLabel` disagreeing with the config's label for that `topicKey` |
| Cross-subject edges | listed for review; most should be deliberate |

### ⚠️ A check that looks obvious and is wrong

Do not flag **"Bloom inversions"** — edges whose prerequisite sits at a higher
Bloom tier than the skill needing it — as errors. This check was built here, it
reported **147 errors**, and hand-review found **3**:

```
MAT_MATRIX16 (Remember: a determinant with two equal rows is zero)
    requires MAT_MATRIX13 (Apply: evaluate a 3×3 determinant)
```

That is the correct order. **Bloom tier measures cognitive demand, not teaching
sequence** — a low-tier *fact about* an operation is routinely learned after the
operation itself. Keep the check as a review list if you like; never as an error.

---

## Pass 6 — Connect near-orphan fragments

**Find:** connected components of 2–6 skills. These pass any "has at least one
edge" gate while being functionally orphaned — under the conjunctive gate, an
island of two is barely different from an isolated node.

**Fix:** for each fragment, propose one edge to an anchor in the same topic.

**Do not automate this.** Two scoring heuristics were tried here:

- *token overlap* — ~40% usable. It proposed lateral links between peers
  (zero-order kinetics "requiring" first-order kinetics; the cosine rule
  "requiring" the sine rule), and returned one pair **in both directions**,
  which would have closed a cycle.
- *topic hub* (lowest Bloom tier, most dependents, overlap only as tiebreak) —
  ~two-thirds usable. Better, still not good enough to apply blind.

Generate proposals mechanically, then **read every one.** Apply the ones you can
justify — several will need reversing from what was proposed. Leave the rest
disconnected and log them. Rejecting roughly a third is a normal, healthy
outcome; a pass that accepts everything has not been reviewed.

---

## Closing report

State plainly:

1. **What was fixed**, with before/after numbers.
2. **What was deliberately left**, and why — especially any edge you declined
   to guess at. This is the handover list for a subject expert.
3. **Any decision a future editor might mistake for an oversight**, with its
   reasoning, so nobody "fixes" it back.
4. **Any check of your own you found to be wrong**, and what you replaced it
   with. On this project two separate heuristics over-flagged by roughly 2×;
   assume yours will too until you have read the hits.
