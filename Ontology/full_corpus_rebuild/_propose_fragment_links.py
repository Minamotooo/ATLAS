"""Propose edges that attach small disconnected fragments to their topic's spine.

THE PROBLEM
-----------
`_edge_coverage.py` measures edges per skill and counts a skill as "connected"
if it has any edge at all. That flatters the graph: a pair of skills joined only
to each other passes the gate while forming an island of two. After the
editorial pass the ontology had 91 components of 6 skills or fewer, holding 281
skills between them - skills that are technically connected and practically
orphaned. Under the conjunctive gate an island that small is barely different
from an isolated node: nothing upstream gates it, and mastering it pulls almost
nothing up.

86 of those 91 fragments sit in a topic that also has a larger component, so the
fix is an edge, not new content.

WHAT THIS DOES
--------------
Read-only. For each small fragment it proposes ONE edge:

    the fragment's own root  ->  requires  ->  an anchor in the same topic

The anchor is chosen from skills in that topic that are (a) in a different
component, (b) at the same Bloom tier or lower than the fragment root, and
(c) closest by token overlap, so the proposal is topically adjacent rather than
merely same-topic. Ties break toward the lower Bloom tier.

The output is a REVIEW LIST, not a patch. Every proposal is a judgement about
what a student needs first, and a wrong prerequisite edge propagates through the
ancestor pull-up - which is exactly the damage this pass exists to avoid. Edges
are applied from `_fragment_links.py`, which holds only the ones that survived
review.

    python _propose_fragment_links.py            # all subjects
    python _propose_fragment_links.py --subject Chemistry
"""
import argparse
import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"

TIER = {"Remember": 1, "Understand": 2, "Apply": 3,
        "Analyze": 4, "Evaluate": 5, "Create": 6}

STOP = {
    "a", "an", "the", "of", "to", "from", "in", "on", "at", "by", "for", "and",
    "or", "with", "its", "it", "that", "this", "which", "as", "is", "are", "be",
    "given", "stated", "named", "specified", "using", "use", "when", "whether",
    "into", "together", "recall", "calculate", "determine", "explain", "write",
    "identify", "classify", "apply", "define", "compare", "predict",
}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower())
            if w not in STOP and len(w) > 2}


def components(tuples, prereqs):
    adj = collections.defaultdict(set)
    for c, v in prereqs.items():
        for p in v:
            adj[c].add(p["id"])
            adj[p["id"]].add(c)
    seen, comps = set(), []
    for t in tuples:
        s = t["skillId"]
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            n = stack.pop()
            comp.append(n)
            for m in adj[n]:
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        comps.append(comp)
    return comps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject")
    ap.add_argument("--max-size", type=int, default=6)
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    D = {t["skillId"]: t for t in tuples}

    parents = collections.defaultdict(set)
    for c, v in prereqs.items():
        for p in v:
            parents[c].add(p["id"])

    comps = components(tuples, prereqs)
    compof = {}
    for i, c in enumerate(comps):
        for s in c:
            compof[s] = i

    bytopic = collections.defaultdict(list)
    for t in tuples:
        bytopic[t["topicKey"]].append(t["skillId"])

    tk = {s: toks(D[s]["skillFull"]) for s in D}
    # how many skills already depend on each skill, directly or transitively-ish
    indeg = collections.Counter()
    for c, v in prereqs.items():
        for p in v:
            indeg[p["id"]] += 1
    proposals = []

    for comp in comps:
        if len(comp) > args.max_size or len(comp) < 2:
            continue
        topic = collections.Counter(D[s]["topicKey"] for s in comp).most_common(1)[0][0]
        if args.subject and D[comp[0]]["subject"] != args.subject:
            continue
        # the fragment's own root: no parent inside the fragment, lowest tier
        inside = set(comp)
        roots = [s for s in comp if not (parents[s] & inside)]
        if not roots:
            roots = comp
        root = min(roots, key=lambda s: (TIER[D[s]["bloom"]], s))

        cands = [s for s in bytopic[topic]
                 if compof[s] != compof[root]
                 and TIER[D[s]["bloom"]] <= TIER[D[root]["bloom"]]]
        if not cands:
            continue

        # Prefer the topic's HUB, not its nearest sibling. The first version of
        # this scored by token overlap alone and kept proposing lateral links
        # between peers - zero-order kinetics "requiring" first-order kinetics,
        # the cosine rule "requiring" the sine rule - which are siblings under a
        # common parent, not prerequisites of each other. Two proposals even came
        # back as a mutual pair, which would have closed a cycle.
        # Ranking by (lower Bloom, more dependents) finds the skill the rest of
        # the topic already rests on, and overlap only breaks ties.
        def score(s):
            a, b = tk[root], tk[s]
            j = len(a & b) / len(a | b) if (a or b) else 0
            return (TIER[D[s]["bloom"]], -indeg[s], -j, s)

        anchor = min(cands, key=score)
        ov = tk[root] & tk[anchor]
        j = len(ov) / len(tk[root] | tk[anchor]) if (tk[root] or tk[anchor]) else 0
        proposals.append((j, topic, comp, root, anchor, sorted(ov)))

    proposals.sort(key=lambda x: (-x[0], x[1]))
    print("fragments needing a link: %d\n" % len(proposals))
    for j, topic, comp, root, anchor, ov in proposals:
        print("[%.2f] %-24s  frag=%d" % (j, topic, len(comp)))
        print("   EDGE  %-24s requires  %s" % (root, anchor))
        print("     child  %-9s %s" % (D[root]["bloom"], D[root]["skillFull"][:96]))
        print("     parent %-9s %s" % (D[anchor]["bloom"], D[anchor]["skillFull"][:96]))
        print("     shared: %s" % (", ".join(ov[:8]) or "(none - weak proposal)"))
    print("\n%d proposals. Review before applying; put survivors in _fragment_links.py"
          % len(proposals))


if __name__ == "__main__":
    main()
