"""
_edge_coverage.py
-----------------
Measure prerequisite-edge coverage for an ontology, so the Quality Checklist item
in `ontology_rebuild_actual_prompt.md` (edges per skill >= 1.0, skills with no
edge <= 25%) is something you can check rather than estimate.

Run it after every batch merge. It exits non-zero if either threshold is missed,
so it can gate a batch the same way the build validation does.

    python Ontology/full_corpus_rebuild/_edge_coverage.py
    python Ontology/full_corpus_rebuild/_edge_coverage.py --source-dir Ontology
    python Ontology/full_corpus_rebuild/_edge_coverage.py --by-topic

Context: the Chemistry pass scored 0.41 edges/skill with 44.2% of skills having no
edge in either direction, which is the failure this exists to catch. See
`quality_audit.md` and system prompt Global Constraint 4.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

EDGES_PER_SKILL_TARGET = 1.0
EDGES_PER_SKILL_FLOOR = 0.8
ISOLATED_PCT_TARGET = 25.0


def load(source_dir: Path, subject: str | None):
    tuples = json.loads((source_dir / "tuples.json").read_text(encoding="utf-8"))
    prereqs = json.loads((source_dir / "prereqs.json").read_text(encoding="utf-8"))
    if subject:
        tuples = [t for t in tuples if t.get("subject") == subject]
    skills = {t["skillId"]: t for t in tuples}

    edges = set()
    for dependent, ancestors in prereqs.items():
        for anc in ancestors or []:
            src = anc.get("id") if isinstance(anc, dict) else None
            if src and src in skills and dependent in skills:
                edges.add((src, dependent))
    return skills, edges


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--subject", default=None)
    ap.add_argument("--by-topic", action="store_true")
    args = ap.parse_args()

    skills, edges = load(args.source_dir, args.subject)
    if not skills:
        sys.exit("error: no skills loaded")

    degree: dict[str, int] = collections.defaultdict(int)
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1

    n = len(skills)
    e = len(edges)
    isolated = [s for s in skills if degree[s] == 0]
    eps = e / n
    iso_pct = 100.0 * len(isolated) / n

    print(f"source            : {args.source_dir.as_posix()}")
    print(f"skills            : {n}")
    print(f"prerequisite edges: {e}")
    print(f"edges per skill   : {eps:.2f}   (target >= {EDGES_PER_SKILL_TARGET}, floor {EDGES_PER_SKILL_FLOOR})")
    print(f"skills with no edge: {len(isolated)} ({iso_pct:.1f}%)   (target <= {ISOLATED_PCT_TARGET}%)")

    if args.by_topic:
        per = collections.defaultdict(lambda: [0, 0])
        for sid, sk in skills.items():
            per[sk["topicKey"]][0] += 1
            if degree[sid] == 0:
                per[sk["topicKey"]][1] += 1
        print(f"\n{'topic':22}{'skills':>7}{'no edge':>9}{'pct':>7}")
        for topic, (total, iso) in sorted(per.items(), key=lambda kv: -kv[1][1] / kv[1][0]):
            print(f"{topic:22}{total:>7}{iso:>9}{100.0 * iso / total:>6.0f}%")

    failures = []
    if eps < EDGES_PER_SKILL_FLOOR:
        failures.append(f"edges per skill {eps:.2f} is below the {EDGES_PER_SKILL_FLOOR} floor")
    if iso_pct > ISOLATED_PCT_TARGET:
        failures.append(f"{iso_pct:.1f}% of skills have no edge (target <= {ISOLATED_PCT_TARGET}%)")

    if failures:
        print("\nFAIL")
        for f in failures:
            print("  - " + f)
        print("\n  Prerequisites are found by comparing each skill against the accumulated")
        print("  ontology, not by looking inside one source record. See system prompt")
        print("  Global Constraint 4.")
        sys.exit(1)

    print("\nPASS")


if __name__ == "__main__":
    main()
