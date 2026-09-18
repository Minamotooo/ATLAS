# Ontology viewers

Standalone, interactive HTML viewers for the skill ontologies in this repo.
Everything here is **generated output plus the one script that generates it** —
nothing in this directory is a source of truth, and nothing here is read by the
backend.

```
viz/
├── build_dag_viewer.py         the generator (the only source file here)
├── all_subjects_rebuild.html   generated — full-corpus rebuild, all 1,624 skills
├── chemistry_rebuild.html      generated — full-corpus rebuild, 843 Chemistry skills
├── mathematics_rebuild.html    generated — full-corpus rebuild, 439 Mathematics skills
├── physics_rebuild.html        generated — full-corpus rebuild, 342 Physics skills
└── chemistry_legacy.html       generated — legacy ontology, 117 Chemistry skills (what the live app runs on)
```

Open either `.html` straight in a browser — no server, no build step.

> **Needs an internet connection to render.** Cytoscape and dagre load from a CDN,
> matching how `Ontology/skill_ontology_dag.html` already works. The ontology data
> itself is embedded in the file, so only the layout libraries are remote.

## Regenerating

```bash
# from the repo root (ATLAS/)
python Ontology/viz/build_dag_viewer.py \
    --source-dir Ontology/full_corpus_rebuild \
    --subject Chemistry \
    --out Ontology/viz/chemistry_rebuild.html \
    --title "Chemistry Skill Ontology — Full-Corpus Rebuild"

python Ontology/viz/build_dag_viewer.py \
    --source-dir Ontology \
    --subject Chemistry \
    --out Ontology/viz/chemistry_legacy.html \
    --title "Chemistry Skill Ontology — Legacy (live app)"
```

To rebuild all four generated views of the rebuild at once:

```bash
for s in Chemistry Mathematics Physics; do
  l=$(echo $s | tr 'A-Z' 'a-z')
  python Ontology/viz/build_dag_viewer.py       --source-dir Ontology/full_corpus_rebuild --subject $s       --out Ontology/viz/${l}_rebuild.html --title "$s — full-corpus rebuild"
done
python Ontology/viz/build_dag_viewer.py     --source-dir Ontology/full_corpus_rebuild     --out Ontology/viz/all_subjects_rebuild.html     --title "ATLAS full-corpus rebuild — all subjects"
```

It works for any ontology defined by a `tuples.json` + `prereqs.json` pair. Drop
`--subject` for every subject at once. Pure stdlib — no dependencies.

**A subject slice silently drops cross-subject edges** and says so in its output
(`edge refs outside this subject slice, dropped: N`). Those edges are real and
present in `all_subjects_rebuild.html` — the per-subject files simply cannot show
them. Use the all-subjects view when the question is about connectivity.

## ⚠️ Why the output is never named `skill_ontology_dag.html`

`Backend/tree_data/build_from_ontology.py::load_source()` treats a file named
**exactly** `skill_ontology_dag.html` inside its `--source-dir` as the
*authoritative* ontology source, **preferring it over `tuples.json` /
`prereqs.json`**. Writing a generated viewer under that name into
`Ontology/full_corpus_rebuild/` would silently change what this documented command
in that directory's `STATUS.md` actually reads:

```bash
python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild ... --report-only
```

So two rules hold here, and the generator enforces the second one by refusing to
write that filename:

1. Generated viewers live in `Ontology/viz/`, which is never passed as a `--source-dir`.
2. No generated viewer is ever named `skill_ontology_dag.html`.

`build_dag_viewer.py` only ever **reads** its source directory.

## How to read the viewer

Two modes, switched from the top bar.

**Topic map** (opens here) — one bubble per topic, area proportional to skill
count. Arrows are prerequisite links that cross a topic boundary, thickness = how
many. This is the one-screen overview; click any bubble to drill into it.

**Skill DAG** — the actual prerequisite graph, laid out top-down so prerequisites
sit above what depends on them. Scoped to one topic by default because drawing all
843 at once is slow and unreadable. Dashed nodes are prerequisites that live in a
*different* topic, pulled in for context.

### Encodings

| Channel | Meaning |
|---|---|
| **Colour** | structural role — *Foundational* (has dependents, no prerequisites), *Intermediate* (both), *Terminal* (has prerequisites, nothing depends on it), *Unconnected* (neither, shown neutral grey) |
| **Size** | degree — total prerequisite + dependent links |
| **Bloom** | a `B1`–`B6` text badge and a sidebar filter — deliberately **not** colour |
| **Layout depth** | prerequisite depth (Skill DAG mode only) |

Bloom is text rather than colour on purpose: six ordered levels don't fit the
validated ordinal colour ramp (it carries five distinguishable steps), and a badge
stays readable for colourblind viewers and in print. Colour went to structural
role instead, which has few enough categories to stay separable — the three role
hues pass colour-vision separation checks in both light and dark mode.

### Topic counts here are *raw*, not canonical

The viewer groups by the `topicKey` written in `tuples.json`. The ontology was
assembled from several drafts, so the same topic appears under 2–3 codes
(`CHE_ATOMIC` vs `CHEM_ATOMIC`, `MAT_` vs `MATH_`), and
`Backend/tree_data/ontology_config.json` merges them only later, during
`build_from_ontology.py`. So expect the viewer's topic count to exceed the
canonical figure quoted elsewhere in the repo:

| Ontology | Raw topics (shown here) | Canonical (after config merge) |
|---|---|---|
| Legacy, all subjects | 115 | 66 |
| Rebuild, all subjects | 134 | 129 |
| Rebuild, Chemistry | 30 | 27 |

That's expected, not a bug — but it does mean two sidebar rows can be the same
real topic under different codes.

Sidebar filters (role, Bloom, search, hide-unconnected) apply to the Skill DAG.
Clicking a node opens a detail panel with its full description, its prerequisites
and its dependents; those are clickable to walk the graph.

Light/dark follows your OS, and the **Theme** button overrides it either way.

## What the files show — and the gap between them

The rebuild is now **complete**: all 4,474 records of all six source books have
been extracted (see `Ontology/full_corpus_rebuild/STATUS.md`).

|  | Legacy (live app) | Full-corpus rebuild |
|---|---|---|
| Skills | 430 | **1,689** |
| Chemistry / Mathematics / Physics | 117 / 170 / 143 | **886 / 447 / 356** |
| Prerequisite edges | 515 | **1,695** |
| Edges per skill | 1.20 | **1.00** |
| Unconnected skills | 0 (0%) | **0 (0%)** |
| Max DAG depth | 7 | **9** |
| Topics populated | 66 | **183 / 183** |

The rebuild has ~3.9x the skill coverage, no unconnected skills at all, and every
one of the 183 syllabus topics populated.
It did not start there. At first consolidation, Chemistry came in at 0.41 edges
per skill with **44.2% of its skills unconnected**, because the extraction prompt
asked a within-record question and the corpus yields only ~1.24 skills per
record, so the answer was almost always "no". That is diagnosed in
`Ontology/full_corpus_rebuild/prereq_sparsity_diagnosis.md`.

Two things closed the gap:

1. **A hand-authored backfill over the existing Chemistry skills**
   (`_backfill_edges.py`): 348 -> 700 edges, 44.2% -> 0.7% unconnected.
2. **A prompt fix** (system prompt Global Constraint 4) applied before
   Mathematics and Physics were extracted. Every one of those eighteen chunks
   came in above 1.0 edges per skill with **zero** unconnected skills, needing no
   backfill at all.

Why this matters beyond aesthetics: `MasteryUpdater`'s conjunctive gate and the
ancestor pull-up both operate on `parent_ids`. A skill with no prerequisites is
never gated and never pulls anything up — it behaves as a free-floating BKT node
with no DAG semantics. Density, not skill count, is what makes an ontology usable.

A third pass closed the rest. The pre-adoption editorial sweep
(`Ontology/full_corpus_rebuild/STATUS.md`) re-filed 1,051 skills onto the right
syllabus topic, authored the 51 foundational skills the corpus assumed but never
taught, split 20 skills that fused two Bloom tiers, merged 7 duplicates and
grounded every remaining isolated node. **Unconnected skills went to zero in all
three subjects**, the largest connected component grew from 203 to 415 and the
DAG deepened from 7 to 9.

Chemistry still trails slightly on density (0.92 against 1.09 and 1.05) and
holds 108 of the 136 fragments — it is the subject whose edges were
reconstructed after the fact rather than extracted alongside the skills. Open
`chemistry_rebuild.html` next to `mathematics_rebuild.html` to see it; the
difference is far more obvious as a picture than as a table.

## Tracking these in git

The `.html` files are generated and fully reproducible from the command above, so
they can be gitignored if you'd rather not track ~440 KB of output:

```gitignore
Ontology/viz/*.html
```

They're left tracked by default so a fresh clone (or anyone you send the repo to)
can open them without running Python first.
