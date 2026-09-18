"""Structural and content validation of the skill ontology.

`build_from_ontology.py` checks that the graph loads and is acyclic. This checks
whether it is *sensible*: whether the edges point the right way, whether skills
sit in the right place, and whether the shape of the graph is one a student can
actually be taken through.

Checks, in the order they are reported:

  E1  isolated skills - no prerequisite, nothing depends on them. Under the
      conjunctive gate they are never gated and never pull anything up, so they
      behave as free-floating BKT nodes with no DAG semantics.
  E2  Bloom inversions - an edge whose prerequisite sits at a HIGHER Bloom tier
      than the skill requiring it. REVIEW ONLY, not an error. The first run of
      this check treated these as defects and was wrong: Bloom tier measures
      cognitive demand, not teaching order, and a low-tier *fact about* an
      operation is routinely learned after the operation.

          MAT_MATRIX16 (Remember: a determinant with two equal rows is zero)
              requires MAT_MATRIX13 (Apply: evaluate a 3x3 determinant)

      is exactly right. Of 147 flagged, hand-review found 3 genuinely reversed.
      The list is kept because that hand-review is worth repeating when edges
      change, not because a hit means something is broken.
      A second reason it cannot be an error: the per-skill `bloom` field is
      never read at runtime. It is not compiled into Backend/tree_data/, the
      diagnostic derives each question's Bloom level from the learner's mastery
      band, and guess/slip comes from that question's level. A skill's stored
      Bloom is provenance, not a control input.
  E3  stale cached text - prereqs.json caches each parent's description; if it
      has drifted from tuples.json the viewers and the compiled catalog will
      disagree.
  E4  orphan topics - a topic whose skills form no internal edges at all, so the
      topic has no internal learning order.
  E5  ungrounded Apply/Analyze skills - a higher-tier skill with no prerequisite
      at all, in a topic that does have lower-tier skills it could rest on.
  E6  singleton topics - one skill only. Usually a retag that did not go far
      enough, or a real coverage gap.
  E7  exact duplicate descriptions that survived the merge pass.
  E8  label drift - topicLabel not matching the label the config gives for that
      topicKey.
  E9  cross-subject edges - listed for review, since most should be deliberate.

Exit code is non-zero if any ERROR-level check fires. WARN-level checks are
reported but do not fail the run.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"
CONFIG = REPO / "Backend" / "tree_data" / "ontology_config.json"

TIER = {"Remember": 1, "Understand": 2, "Apply": 3,
        "Analyze": 4, "Evaluate": 5, "Create": 6}

errors = 0
warns = 0


def report(level, code, title, items, show=12):
    global errors, warns
    if not items:
        print("  ok   %-4s %s" % (code, title))
        return
    if level == "ERROR":
        errors += 1
    else:
        warns += 1
    print("  %-5s %-4s %s: %d" % (level, code, title, len(items)))
    for x in items[:show]:
        print("           %s" % x)
    if len(items) > show:
        print("           ... and %d more" % (len(items) - show))


def main():
    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    labels = cfg["topic_labels"]

    by_id = {t["skillId"]: t for t in tuples}
    edges = [(c, p["id"]) for c, v in prereqs.items() for p in v]

    print("ontology: %d skills, %d edges, %d topics, %d subjects\n"
          % (len(tuples), len(edges),
             len({t["topicKey"] for t in tuples}),
             len({t["subject"] for t in tuples})))

    deg = collections.Counter()
    for c, p in edges:
        deg[c] += 1
        deg[p] += 1

    # E1 isolated
    iso = ["%s [%s] %s" % (t["skillId"], t["topicKey"], t["skillFull"][:70])
           for t in tuples if deg[t["skillId"]] == 0]
    report("WARN", "E1", "isolated skills", iso)

    # E2 bloom inversions
    inv = []
    for c, p in edges:
        if c in by_id and p in by_id:
            tc, tp = TIER.get(by_id[c]["bloom"], 3), TIER.get(by_id[p]["bloom"], 3)
            if tp > tc:
                inv.append("%s(%s) requires %s(%s)"
                           % (c, by_id[c]["bloom"], p, by_id[p]["bloom"]))
    report("WARN", "E2", "Bloom inversions (review only, see docstring)", inv, show=6)

    # E3 stale cached text
    stale = []
    for c, plist in prereqs.items():
        for p in plist:
            if p["id"] in by_id and p.get("full") != by_id[p["id"]]["skillFull"]:
                stale.append("%s -> %s" % (c, p["id"]))
    report("ERROR", "E3", "stale cached prerequisite text", stale)

    # E4 topics with no internal edge
    topic_of = {t["skillId"]: t["topicKey"] for t in tuples}
    internal = collections.Counter()
    for c, p in edges:
        if topic_of.get(c) and topic_of.get(c) == topic_of.get(p):
            internal[topic_of[c]] += 1
    sizes = collections.Counter(t["topicKey"] for t in tuples)
    orphan = ["%s (%d skills, no internal edge)" % (k, n)
              for k, n in sorted(sizes.items()) if n >= 3 and internal[k] == 0]
    report("WARN", "E4", "topics with no internal learning order", orphan, show=20)

    # E5 ungrounded higher-tier skills
    has_parent = {c for c, _ in edges}
    lower_in_topic = collections.defaultdict(int)
    for t in tuples:
        if TIER.get(t["bloom"], 3) <= 2:
            lower_in_topic[t["topicKey"]] += 1
    ung = ["%s [%s/%s] %s" % (t["skillId"], t["topicKey"], t["bloom"], t["skillFull"][:60])
           for t in tuples
           if TIER.get(t["bloom"], 3) >= 3
           and t["skillId"] not in has_parent
           and lower_in_topic[t["topicKey"]] > 0]
    report("WARN", "E5", "higher-tier skills with no prerequisite", ung, show=15)

    # E6 singleton topics
    single = ["%s (%s)" % (k, labels.get(k)) for k, n in sorted(sizes.items()) if n == 1]
    report("WARN", "E6", "topics holding a single skill", single, show=20)

    # E7 exact duplicate text
    seen = collections.defaultdict(list)
    for t in tuples:
        seen[t["skillFull"].strip().lower()].append(t["skillId"])
    dup = ["%s  |  %s" % (" = ".join(v), k[:80]) for k, v in seen.items() if len(v) > 1]
    report("WARN", "E7", "exact duplicate descriptions", dup, show=20)

    # E8 label drift
    drift = []
    for t in tuples:
        lab = labels.get(t["topicKey"])
        want = lab if isinstance(lab, str) else (lab or {}).get("en")
        if want and t.get("topicLabel") != want:
            drift.append("%s: %r != %r" % (t["skillId"], t.get("topicLabel"), want))
    report("ERROR", "E8", "topicLabel drift", drift)

    # E9 cross-subject edges
    xs = []
    for c, p in edges:
        if c in by_id and p in by_id and by_id[c]["subject"] != by_id[p]["subject"]:
            xs.append("%s(%s) <- %s(%s)"
                      % (c, by_id[c]["subject"][:4], p, by_id[p]["subject"][:4]))
    report("WARN", "E9", "cross-subject edges (review)", xs, show=20)

    # shape summary
    parents = collections.defaultdict(set)
    children = collections.defaultdict(set)
    for c, p in edges:
        parents[c].add(p)
        children[p].add(c)
    adj = collections.defaultdict(set)
    for c, p in edges:
        adj[c].add(p)
        adj[p].add(c)
    seenc, comps = set(), []
    for t in tuples:
        s = t["skillId"]
        if s in seenc:
            continue
        stack, comp = [s], []
        seenc.add(s)
        while stack:
            n = stack.pop()
            comp.append(n)
            for m in adj[n]:
                if m not in seenc:
                    seenc.add(m)
                    stack.append(m)
        comps.append(len(comp))
    comps.sort(reverse=True)
    print("\n  shape: %d components, largest %d, singletons %d"
          % (len(comps), comps[0], sum(1 for c in comps if c == 1)))
    print("  roots: %d   leaves: %d"
          % (sum(1 for t in tuples if not parents[t["skillId"]]),
             sum(1 for t in tuples if not children[t["skillId"]])))
    bl = collections.Counter(t["bloom"] for t in tuples)
    print("  bloom: %s" % dict(sorted(bl.items(), key=lambda kv: TIER.get(kv[0], 9))))

    print("\n%s  (%d error-level, %d warn-level)"
          % ("FAIL" if errors else "PASS", errors, warns))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
