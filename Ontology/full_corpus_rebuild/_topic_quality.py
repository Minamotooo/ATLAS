"""Rank every topic in the ontology by how well-formed it is.

Not all 183 topics are equally good, and the aggregate numbers hide that. This
scores each topic on the five properties that decide whether the adaptive engine
can actually teach it, then prints the best and the worst.

THE FIVE CRITERIA
-----------------
1. GROUNDED   - what fraction of its skills came from real corpus questions
                rather than being hand-authored. An authored skill has no past
                question behind it, so the RAG retriever has nothing to ground
                generation on.
2. LADDER     - how many distinct Bloom levels its skills span. NOTE: this is
                NOT an engine requirement. The per-skill `bloom` field is never
                read at runtime - it is not even compiled into
                Backend/tree_data/. `diagnostic.py::_select_bloom` derives each
                question's level from the LEARNER's mastery band, and the
                generator expands every skill to all six levels regardless.
                What this criterion actually measures is the cognitive spread of
                the SOURCE QUESTIONS behind the topic: a topic whose questions
                only ever asked recall is thinner corpus evidence than one whose
                questions ranged from recall to analysis. Useful signal, but
                indirect - read it that way.
3. INTERNAL   - internal edges per skill. A topic with no internal edges has no
                learning order of its own, only a label.
4. REACH      - what fraction of its skills sit in the largest connected
                component OF THEIR OWN SUBJECT, so that mastering them
                propagates through the ancestor pull-up instead of dead-ending.
                Measured per subject on purpose: the three subjects are largely
                separate graphs joined by only 18 deliberate cross-subject
                edges, and the ontology-wide largest component is 98% Chemistry.
                Scoring Mathematics and Physics against it would zero them both
                for no reason that reflects their quality.
5. SIZE       - 5 to 25 skills is the workable band. Below that the topic cannot
                localise a gap; far above it, one "topic" is really several and
                a diagnostic cannot say what the student actually missed.

Each is normalised to 0-1 and averaged. The score is a rough instrument - it
measures the SHAPE of a topic, not whether its chemistry is right. A topic can
score 1.00 and still contain a wrong prerequisite edge; only a subject expert
catches that.

    python _topic_quality.py              # best 12 and worst 12
    python _topic_quality.py --all        # every topic
    python _topic_quality.py --subject Physics
"""
import argparse
import collections
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--subject")
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    D = {t["skillId"]: t for t in tuples}

    edges = [(c, p["id"]) for c, v in prereqs.items() for p in v]

    # main connected component
    adj = collections.defaultdict(set)
    for c, p in edges:
        adj[c].add(p)
        adj[p].add(c)
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
    # largest component within each subject, not ontology-wide (see docstring)
    main_comp = set()
    for subj in {t["subject"] for t in tuples}:
        best, bestn = None, -1
        for c in comps:
            k = sum(1 for s in c if D[s]["subject"] == subj)
            if k > bestn:
                best, bestn = c, k
        main_comp |= {s for s in best if D[s]["subject"] == subj}

    bytopic = collections.defaultdict(list)
    for t in tuples:
        bytopic[t["topicKey"]].append(t)

    internal = collections.Counter()
    for c, p in edges:
        if c in D and p in D and D[c]["topicKey"] == D[p]["topicKey"]:
            internal[D[c]["topicKey"]] += 1

    rows = []
    for topic, skills in bytopic.items():
        if args.subject and skills[0]["subject"] != args.subject:
            continue
        n = len(skills)
        grounded = sum(1 for s in skills if not s.get("authored")) / n
        ladder = min(len({s["bloom"] for s in skills}) / 3.0, 1.0)
        internal_ps = min(internal[topic] / n, 1.0)
        reach = sum(1 for s in skills if s["skillId"] in main_comp) / n
        if n < 5:
            size = n / 5.0
        elif n <= 25:
            size = 1.0
        else:
            size = max(0.0, 1.0 - (n - 25) / 30.0)
        score = (grounded + ladder + internal_ps + reach + size) / 5.0
        rows.append((score, topic, skills[0]["subject"], n,
                     grounded, ladder, internal_ps, reach, size))

    rows.sort(reverse=True)
    hdr = ("%-26s %-5s %4s  %6s %6s %6s %6s %6s   %s"
           % ("topic", "subj", "n", "score", "grnd", "ladr", "intl", "reach", "size"))

    def show(rs):
        print(hdr)
        print("-" * len(hdr))
        for sc, tp, sub, n, g, l, i, r, z in rs:
            print("%-26s %-5s %4d  %6.2f %6.2f %6.2f %6.2f %6.2f   %.2f"
                  % (tp, sub[:4], n, sc, g, l, i, r, z))

    if args.all:
        show(rows)
    else:
        print("=== STRONGEST %d TOPICS ===\n" % args.n)
        show(rows[:args.n])
        print("\n\n=== WEAKEST %d TOPICS ===\n" % args.n)
        show(rows[-args.n:])
    print("\n%d topics scored. Mean %.2f, median %.2f"
          % (len(rows), sum(r[0] for r in rows) / len(rows),
             sorted(r[0] for r in rows)[len(rows) // 2]))


if __name__ == "__main__":
    main()
