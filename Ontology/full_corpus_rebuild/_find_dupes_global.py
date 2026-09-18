"""Find near-duplicate skills across the WHOLE ontology.

The `_find_near_dupes*.py` family only ever compared skills sharing a
`topicKey`, and only within one batch at a time. That missed two whole classes
of duplicate:

  - the same skill extracted into two different topics (flame-test colours
    appeared in both qualitative analysis and descriptive chemistry);
  - duplicates in Mathematics and Physics, for which the check was never run
    at all.

This compares every pair in the ontology. It is read-only: it reports, it does
not merge. Merging is a judgement call and lives in `_merge_dupes.py`.

Scoring combines a token-set Jaccard with a sequence ratio, because the two
disagree in useful ways: Jaccard catches reordered phrasing, the sequence ratio
catches near-identical wording with one changed number.

    python _find_dupes_global.py            # default threshold
    python _find_dupes_global.py --min 0.80
"""
import argparse
import difflib
import itertools
import json
import pathlib
import re
import collections

HERE = pathlib.Path(__file__).resolve().parent
TUPLES = HERE / "tuples.json"

STOP = {
    "a", "an", "the", "of", "to", "from", "in", "on", "at", "by", "for", "and",
    "or", "with", "its", "it", "that", "this", "which", "as", "is", "are",
    "be", "given", "stated", "named", "specified", "using", "use", "when",
    "whether", "into", "together",
}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.72)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    rows = [(t["skillId"], t["skillFull"], t["topicKey"], t["subject"], t["bloom"])
            for t in tuples]
    tokens = {r[0]: toks(r[1]) for r in rows}

    # blocking: only compare pairs that share at least one uncommon token,
    # otherwise this is 1.4M sequence-ratio calls for nothing.
    index = collections.defaultdict(list)
    df = collections.Counter()
    for sid, tk in tokens.items():
        for w in tk:
            df[w] += 1
    for sid, tk in tokens.items():
        for w in tk:
            if df[w] <= 120:
                index[w].append(sid)

    cand = set()
    for w, ids in index.items():
        if len(ids) < 2:
            continue
        for a, b in itertools.combinations(sorted(ids), 2):
            cand.add((a, b))

    by_id = {r[0]: r for r in rows}
    hits = []
    for a, b in cand:
        ta, tb = tokens[a], tokens[b]
        if not ta or not tb:
            continue
        jac = len(ta & tb) / len(ta | tb)
        if jac < 0.45:
            continue
        seq = difflib.SequenceMatcher(None, by_id[a][1].lower(), by_id[b][1].lower()).ratio()
        score = 0.5 * jac + 0.5 * seq
        if score >= args.min:
            hits.append((score, jac, seq, a, b))

    hits.sort(reverse=True)
    same_topic = sum(1 for h in hits if by_id[h[3]][2] == by_id[h[4]][2])
    print("pairs compared      : %d" % len(cand))
    print("candidates >= %.2f  : %d   (%d same-topic, %d CROSS-topic)"
          % (args.min, len(hits), same_topic, len(hits) - same_topic))
    print()
    for score, jac, seq, a, b in hits[:args.limit]:
        ra, rb = by_id[a], by_id[b]
        mark = "SAME " if ra[2] == rb[2] else "CROSS"
        print("%s %.3f (j%.2f s%.2f)" % (mark, score, jac, seq))
        print("   %-22s %-9s %-24s %s" % (a, ra[4], ra[2], ra[1][:104]))
        print("   %-22s %-9s %-24s %s" % (b, rb[4], rb[2], rb[1][:104]))


if __name__ == "__main__":
    main()
