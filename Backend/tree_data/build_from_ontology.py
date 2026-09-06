"""
build_from_ontology.py
----------------------
Build every ontology artifact the platform needs from the admission-test skill map.

Inputs
------
  ontology_source/skill_ontology_dag.html   authoritative — embeds NODES, EDGES,
                                            TOPIC_META, SUBJECT_ORDER, SUBJECT_TOPIC_ORDER
  ontology_source/tuples.json               fallback if the HTML is absent
  ontology_source/prereqs.json              fallback edge source
  ontology_config.json                      editorial layer: topic aliases, labels, catalog

Outputs (--out-dir, default tree_data/generated/)
------------------------------------------------
  topic_skills.json        { canonical_topic_code: [skill_id, ...] }
  skill_descriptions.json  { skill_id: description }
  skill_edges.json         [ {source, target}, ... ]     direct edges, transitively reduced
  skill_subjects.json      { skill_id: "Mathematics" | "Physics" | "Chemistry" }
  topic_labels.json        { canonical_topic_code: label }
  topic_subjects.json      { canonical_topic_code: subject }
  topic_resolution.json    every raw code/label -> canonical code (for the question loader)
  platform_catalog.json    courses -> sections -> topics, built from ontology_config.json

Why the HTML is authoritative
-----------------------------
It is the only source carrying TOPIC_META (topic -> label + subject) and
SUBJECT_TOPIC_ORDER (syllabus order). Its EDGES list is verified identical to the
edge set derivable from prereqs.json, so nothing is lost by preferring it.

Two structural corrections applied here
---------------------------------------
1. Transitive reduction. prereqs.json lists ancestors, not direct edges, and its
   `depth` field is uniformly 0. Taken literally it yields shortcut edges (A->C
   alongside A->B->C). That matters because MasteryUpdater's conjunctive gate reads
   parent_ids: a shortcut would let a skill unlock while its true intermediate
   prerequisite is still unmastered.
2. Topic canonicalization. The source ontology was assembled from three drafts, so
   the same topic appears under 2-3 codes. ontology_config.json maps them to one.

Usage
-----
    python Backend/tree_data/build_from_ontology.py --report-only
    python Backend/tree_data/build_from_ontology.py --out-dir Backend/tree_data --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "ontology_source"
CONFIG_PATH = HERE / "ontology_config.json"

GENERATED_FILES = (
    "topic_skills.json",
    "skill_descriptions.json",
    "skill_edges.json",
    "skill_subjects.json",
    "topic_labels.json",
    "topic_subjects.json",
    "topic_resolution.json",
    "platform_catalog.json",
)

BLOOM_ORDER = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------
def load_json(path: Path):
    if not path.is_file():
        raise SystemExit(f"ERROR: file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: {path} is not valid JSON: {exc}")


def extract_js_const(src: str, name: str):
    """Pull `const NAME = <json>;` out of the visualizer HTML."""
    match = re.search(r"^const\s+" + name + r"\s*=\s*(.+?);\s*$", src, re.M | re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def load_source(source_dir: Path) -> dict:
    """
    Return {nodes, edges, topic_meta, subject_order, subject_topic_order}.
    Prefers the HTML; falls back to tuples.json + prereqs.json.
    """
    html = source_dir / "skill_ontology_dag.html"
    if html.is_file():
        src = html.read_text(encoding="utf-8")
        nodes = extract_js_const(src, "NODES")
        edges = extract_js_const(src, "EDGES")
        topic_meta = extract_js_const(src, "TOPIC_META")
        if nodes and edges is not None and topic_meta:
            print(f"source: {html.name} (authoritative)")
            # tuples.json labels the same topic differently in places, and the
            # question generator reads tuples.json — so its labels are what end up
            # stamped on generated questions. Collect them for the resolution table.
            alt_labels: Dict[str, Set[str]] = defaultdict(set)
            tuples_path = source_dir / "tuples.json"
            if tuples_path.is_file():
                try:
                    for item in json.loads(tuples_path.read_text(encoding="utf-8")):
                        if isinstance(item, dict) and item.get("topicKey") and item.get("topicLabel"):
                            alt_labels[item["topicKey"]].add(item["topicLabel"])
                except json.JSONDecodeError:
                    pass
            return {
                "nodes": nodes,
                "edges": [(a, b) for a, b in edges],
                "topic_meta": topic_meta,
                "alt_labels": {k: sorted(v) for k, v in alt_labels.items()},
                "subject_order": extract_js_const(src, "SUBJECT_ORDER") or [],
                "subject_topic_order": extract_js_const(src, "SUBJECT_TOPIC_ORDER") or {},
            }
        print(f"warn: could not parse {html.name}; falling back to JSON sources")

    tuples = load_json(source_dir / "tuples.json")
    prereqs = load_json(source_dir / "prereqs.json")
    print("source: tuples.json + prereqs.json")

    nodes = [
        {
            "id": t["skillId"],
            "full": t.get("skillFull", ""),
            "tp": t.get("topicKey", "UNASSIGNED"),
            "subject": t.get("subject", ""),
            "bloom": t.get("bloom", ""),
        }
        for t in (tuples if isinstance(tuples, list) else [tuples])
        if isinstance(t, dict) and t.get("skillId")
    ]
    edges = [
        (a["id"], child)
        for child, ancestors in prereqs.items()
        for a in (ancestors or [])
        if isinstance(a, dict) and a.get("id")
    ]
    topic_meta: Dict[str, dict] = {}
    for t in tuples:
        code = t.get("topicKey")
        if code and code not in topic_meta:
            topic_meta[code] = {
                "label": t.get("topicLabel", code),
                "subject": t.get("subject", ""),
            }
    return {
        "nodes": nodes,
        "edges": edges,
        "topic_meta": topic_meta,
        "subject_order": [],
        "subject_topic_order": {},
    }


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------
def find_cycle(children: Dict[str, Set[str]]) -> Optional[List[str]]:
    """One cycle as a node list, or None. Iterative three-colour DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    colour: Dict[str, int] = {n: WHITE for n in children}

    for root in children:
        if colour[root] != WHITE:
            continue
        stack: List[Tuple[str, Iterable[str]]] = [(root, iter(sorted(children[root])))]
        path: List[str] = [root]
        colour[root] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for child in it:
                if colour.get(child, WHITE) == GRAY:
                    return path[path.index(child):] + [child]
                if colour.get(child, WHITE) == WHITE:
                    colour[child] = GRAY
                    path.append(child)
                    stack.append((child, iter(sorted(children.get(child, set())))))
                    advanced = True
                    break
            if not advanced:
                colour[node] = BLACK
                path.pop()
                stack.pop()
    return None


def transitive_reduction(
    children: Dict[str, Set[str]]
) -> Tuple[Dict[str, Set[str]], List[Tuple[str, str]]]:
    """Drop edges implied by a longer path. Assumes acyclic."""
    reduced = {u: set(vs) for u, vs in children.items()}
    dropped: List[Tuple[str, str]] = []

    for u in sorted(children):
        direct = sorted(children[u])
        if len(direct) < 2:
            continue
        for v in direct:
            seen: Set[str] = set()
            stack = [w for w in direct if w != v]
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                if node == v:
                    reduced[u].discard(v)
                    dropped.append((u, v))
                    break
                stack.extend(children.get(node, ()))
    return reduced, dropped


def compute_depths(children: Dict[str, Set[str]], all_nodes: Set[str]) -> Dict[str, int]:
    parents: Dict[str, Set[str]] = {n: set() for n in all_nodes}
    for u, vs in children.items():
        for v in vs:
            parents[v].add(u)
    in_degree = {n: len(parents[n]) for n in all_nodes}
    queue = [n for n, d in in_degree.items() if d == 0]
    depths = {n: 0 for n in all_nodes}
    while queue:
        node = queue.pop()
        for child in children.get(node, ()):
            depths[child] = max(depths[child], depths[node] + 1)
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    return depths


def connected_components(children: Dict[str, Set[str]], all_nodes: Set[str]) -> List[int]:
    adj: Dict[str, Set[str]] = defaultdict(set)
    for u, vs in children.items():
        for v in vs:
            adj[u].add(v)
            adj[v].add(u)
    seen: Set[str] = set()
    sizes: List[int] = []
    for node in all_nodes:
        if node in seen:
            continue
        stack, comp = [node], set()
        while stack:
            cur = stack.pop()
            if cur in comp:
                continue
            comp.add(cur)
            stack.extend(adj[cur] - comp)
        seen |= comp
        sizes.append(len(comp))
    return sorted(sizes, reverse=True)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(source: dict, config: dict) -> dict:
    report: Dict[str, object] = {}
    aliases: Dict[str, str] = config.get("topic_aliases", {})
    label_overrides: Dict[str, str] = config.get("topic_labels", {})

    def canonical(topic_code: str) -> str:
        return aliases.get(topic_code, topic_code)

    nodes = source["nodes"]
    topic_meta = source["topic_meta"]

    descriptions: Dict[str, str] = {}
    subjects: Dict[str, str] = {}
    topic_subjects: Dict[str, str] = {}
    topic_to_skills: Dict[str, List[str]] = defaultdict(list)
    blooms_per_skill: Dict[str, Set[str]] = defaultdict(set)

    for node in nodes:
        sid = node["id"]
        descriptions.setdefault(sid, node.get("full") or "")
        if node.get("subject"):
            subjects.setdefault(sid, node["subject"])
        if node.get("bloom"):
            blooms_per_skill[sid].add(node["bloom"])

        code = canonical(node.get("tp") or "UNASSIGNED")
        if sid not in topic_to_skills[code]:
            topic_to_skills[code].append(sid)
        meta = topic_meta.get(node.get("tp"), {})
        if meta.get("subject"):
            topic_subjects.setdefault(code, meta["subject"])

    all_skills = set(descriptions)

    # --- labels -------------------------------------------------------------
    topic_labels: Dict[str, str] = {}
    for code in topic_to_skills:
        if code in label_overrides:
            topic_labels[code] = label_overrides[code]
        else:
            raw = topic_meta.get(code, {}).get("label", code)
            # Strip leading syllabus numbering ("15 · Modern Physics").
            topic_labels[code] = re.sub(r"^\s*[\d.]+\s*[·•.:\-]\s*", "", str(raw)).strip() or code

    # --- edges --------------------------------------------------------------
    children: Dict[str, Set[str]] = {sid: set() for sid in all_skills}
    unknown_edge_nodes: Set[str] = set()
    self_edges: List[str] = []
    raw_edges = 0

    for parent, child in source["edges"]:
        if parent not in all_skills or child not in all_skills:
            unknown_edge_nodes.update({parent, child} - all_skills)
            continue
        if parent == child:
            self_edges.append(parent)
            continue
        children[parent].add(child)
        raw_edges += 1

    cycle = find_cycle(children)
    if cycle:
        report["cycle"] = cycle
        return {"ok": False, "report": report}

    reduced, dropped = transitive_reduction(children)
    edges = [
        {"source": p, "target": c} for p in sorted(reduced) for c in sorted(reduced[p])
    ]

    depths = compute_depths(reduced, all_skills)
    parent_count: Dict[str, int] = defaultdict(int)
    for p, kids in reduced.items():
        for k in kids:
            parent_count[k] += 1

    # --- resolution table ---------------------------------------------------
    # The generator stamps questions with the RAW topicLabel from tuples.json, but
    # the DB stores canonical codes. Give the loader every string that should map
    # to a canonical code so it never has to guess.
    resolution: Dict[str, str] = {}
    for raw_code, meta in topic_meta.items():
        canon = canonical(raw_code)
        if canon not in topic_to_skills:
            continue
        resolution[raw_code] = canon
        raw_label = str(meta.get("label", "")).strip()
        if raw_label:
            resolution[raw_label] = canon
            stripped = re.sub(r"^\s*[\d.]+\s*[·•.:\-]\s*", "", raw_label).strip()
            if stripped:
                resolution[stripped] = canon
    for raw_code, labels in (source.get("alt_labels") or {}).items():
        canon = canonical(raw_code)
        if canon not in topic_to_skills:
            continue
        for label in labels:
            label = str(label).strip()
            if not label:
                continue
            resolution[label] = canon
            stripped = re.sub(r"^\s*[\d.]+\s*[·•.:\-]\s*", "", label).strip()
            if stripped:
                resolution.setdefault(stripped, canon)

    # Canonical code/label always win over any raw alias above.
    for code, label in topic_labels.items():
        resolution[code] = code
        resolution[label] = code

    # --- catalog ------------------------------------------------------------
    catalog, catalog_report = build_catalog(config, topic_to_skills, topic_labels)

    incomplete_bloom = {
        sid: sorted(bl, key=lambda b: BLOOM_ORDER.index(b) if b in BLOOM_ORDER else 99)
        for sid, bl in blooms_per_skill.items()
        if len(bl) < len(BLOOM_ORDER)
    }

    report.update(
        {
            "cycle": None,
            "skills_total": len(all_skills),
            "topics_raw": len(topic_meta),
            "topics_canonical": len(topic_to_skills),
            "topics_merged": len({k for k in aliases if k in topic_meta}),
            "edges_raw": raw_edges,
            "edges_after_reduction": len(edges),
            "edges_dropped_redundant": dropped,
            "self_edges_dropped": sorted(set(self_edges)),
            "unknown_edge_nodes": sorted(unknown_edge_nodes),
            "roots": sorted(s for s in all_skills if parent_count[s] == 0),
            "max_depth": max(depths.values(), default=0),
            "component_sizes": connected_components(reduced, all_skills),
            "skills_missing_description": sorted(s for s, d in descriptions.items() if not d),
            "skills_missing_subject": sorted(all_skills - set(subjects)),
            "skills_with_partial_bloom_coverage": incomplete_bloom,
            "subjects": sorted(set(subjects.values())),
            **catalog_report,
        }
    )

    return {
        "ok": True,
        "report": report,
        "topic_skills": {k: sorted(v) for k, v in sorted(topic_to_skills.items())},
        "skill_descriptions": dict(sorted(descriptions.items())),
        "skill_edges": edges,
        "skill_subjects": dict(sorted(subjects.items())),
        "topic_labels": dict(sorted(topic_labels.items())),
        "topic_subjects": dict(sorted(topic_subjects.items())),
        "topic_resolution": dict(sorted(resolution.items())),
        "platform_catalog": catalog,
    }


def build_catalog(
    config: dict,
    topic_to_skills: Dict[str, List[str]],
    topic_labels: Dict[str, str],
) -> Tuple[dict, dict]:
    """Turn the editorial course/section layout into platform_catalog.json."""
    courses = []
    placed: Set[str] = set()
    empty_sections: List[str] = []
    unknown_topics: List[str] = []

    for course in config.get("courses", []):
        sections = []
        for section in course.get("sections", []):
            topics = []
            for code in section.get("topics", []):
                if code not in topic_to_skills:
                    unknown_topics.append(f"{section['id']}:{code}")
                    continue
                placed.add(code)
                topics.append(
                    {
                        "id": code.lower(),
                        "title": topic_labels.get(code, code),
                        "skill_topic_code": code,
                    }
                )
            if not topics:
                empty_sections.append(section["id"])
            sections.append(
                {
                    "id": section["id"],
                    "title": section["title"],
                    "title_bn": section.get("title_bn", section["title"]),
                    "enabled": bool(topics),
                    "topics": topics,
                }
            )
        courses.append(
            {
                "id": course["id"],
                "title": course["title"],
                "title_bn": course.get("title_bn", course["title"]),
                "subject": course.get("subject", course["title"]),
                "enabled": any(s["enabled"] for s in sections),
                "sections": sections,
            }
        )

    return {"courses": courses}, {
        "catalog_topics_placed": len(placed),
        "catalog_topics_unplaced": sorted(set(topic_to_skills) - placed),
        "catalog_empty_sections": empty_sections,
        "catalog_unknown_topics": unknown_topics,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_report(report: dict, verbose: bool) -> None:
    if report.get("cycle"):
        print("\nFAILED: prerequisite graph contains a cycle.")
        print("  " + " -> ".join(report["cycle"]))
        return

    print("\n--- ontology report ---")
    print(f"  skills                : {report['skills_total']}")
    print(f"  topics  raw           : {report['topics_raw']}")
    print(f"          canonical     : {report['topics_canonical']}  "
          f"({report['topics_merged']} codes merged by ontology_config.json)")
    print(f"  subjects              : {', '.join(report['subjects']) or '(none)'}")
    print(f"  edges   raw           : {report['edges_raw']}")
    print(f"          reduced       : {report['edges_after_reduction']} "
          f"({len(report['edges_dropped_redundant'])} redundant dropped)")
    print(f"  root skills           : {len(report['roots'])}")
    print(f"  max DAG depth         : {report['max_depth']}")
    sizes = report["component_sizes"]
    print(f"  components            : {len(sizes)} (largest {sizes[0] if sizes else 0})")

    print(f"\n  catalog topics placed : {report['catalog_topics_placed']}")
    unplaced = report["catalog_topics_unplaced"]
    if unplaced:
        print(f"  WARN {len(unplaced)} topics are not in any section (ingested but invisible):")
        for code in unplaced[:12]:
            print(f"    - {code}")
        if len(unplaced) > 12:
            print(f"    ... and {len(unplaced) - 12} more")
    if report["catalog_unknown_topics"]:
        print(f"  WARN sections reference {len(report['catalog_unknown_topics'])} unknown topics:")
        for item in report["catalog_unknown_topics"][:10]:
            print(f"    - {item}")
    if report["catalog_empty_sections"]:
        print(f"  WARN empty sections (disabled): {', '.join(report['catalog_empty_sections'])}")

    for key, label in (
        ("skills_missing_description", "skills have no description"),
        ("skills_missing_subject", "skills have no subject"),
        ("unknown_edge_nodes", "edge endpoints are not known skills"),
    ):
        items = report.get(key) or []
        if items:
            print(f"\n  WARN {len(items)} {label}: {', '.join(items[:8])}"
                  f"{' ...' if len(items) > 8 else ''}")

    partial = report["skills_with_partial_bloom_coverage"]
    if partial:
        print(f"\n  NOTE {len(partial)} skills carry fewer than {len(BLOOM_ORDER)} Bloom levels.")
        print("    The diagnostic tests one Bloom level ABOVE current mastery, so sparse")
        print("    Bloom coverage makes the nearby-Bloom fallback the normal path.")

    if verbose and report["edges_dropped_redundant"]:
        print("\n  redundant edges removed:")
        for p, c in report["edges_dropped_redundant"]:
            print(f"    {p} -> {c}")


def write_outputs(built: dict, out_dir: Path, force: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [n for n in GENERATED_FILES if (out_dir / n).exists()]
    if existing and not force:
        raise SystemExit(
            f"\nERROR: {out_dir} already contains {', '.join(existing[:4])}...\n"
            "Re-run with --force, or use a different --out-dir and diff first."
        )

    payloads = {
        "topic_skills.json": built["topic_skills"],
        "skill_descriptions.json": built["skill_descriptions"],
        "skill_edges.json": built["skill_edges"],
        "skill_subjects.json": built["skill_subjects"],
        "topic_labels.json": built["topic_labels"],
        "topic_subjects.json": built["topic_subjects"],
        "topic_resolution.json": built["topic_resolution"],
        "platform_catalog.json": built["platform_catalog"],
    }
    print(f"\nWriting to {out_dir}")
    for name, data in payloads.items():
        with (out_dir / name).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ontology artifacts for ATLAS.")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--out-dir", type=Path, default=HERE / "generated")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    source = load_source(args.source_dir)
    config = load_json(args.config)
    print(f"config: {args.config.name}")
    print(f"loaded {len(source['nodes'])} nodes, {len(source['edges'])} edges, "
          f"{len(source['topic_meta'])} topics")

    built = build(source, config)
    print_report(built["report"], verbose=args.verbose)
    if not built["ok"]:
        return 1

    if args.report_only:
        print("\n(report-only; nothing written)")
        return 0

    write_outputs(built, args.out_dir, args.force)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
