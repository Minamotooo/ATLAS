"""Merge the true duplicates found by `_find_dupes_global.py`, and handle the
cross-subject overlaps.

THREE KINDS OF FINDING, THREE DIFFERENT ANSWERS
-----------------------------------------------
1. MERGES - the same skill extracted twice. One id survives, the loser's edges
   are rewired onto the winner and the loser is deleted. Six of these.

2. CROSS_SUBJECT - HSC teaches some skills in two subjects. Higher Math 2nd
   Paper has a Dynamics chapter that repeats Physics 1st Paper kinematics
   almost word for word, and Physics uses the vector products taught in Higher
   Math 1st Paper. These are NOT merged, because each subject's catalog needs
   its own section to be populated - deleting the Mathematics copies would
   empty MAT2_PLANE_MOTION and MAT2_PROJECTILE entirely.
   Instead each pair is linked by a prerequisite edge pointing at whichever
   subject teaches it first and more fundamentally (Physics for kinematics and
   projectiles, Mathematics for vector algebra), and both nodes are marked
   `crossSubjectEquivalent`. The edge is what makes mastery propagate: under
   the ancestor pull-up, a student who proves the skill in one subject is
   credited in the other. Merging them properly needs a schema that lets one
   skill sit in two topics, which the current `topicKey` field cannot express -
   the marking is there so that change can find them later.

3. TIER_EDGES - pairs that look alike because one is the Remember statement of
   a formula and the other the Apply that uses it. Correct as two skills; they
   were just missing the edge between them.

`--dry-run` reports and writes nothing.
"""
import argparse
import collections
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"
BACKUP = HERE / "_prefix_backup"

# loser -> (winner, replacement text for the winner or None to keep it)
MERGES = {
    # three separate extractions of "recall the flame-test colour of a cation":
    # two from qualitative analysis, one from descriptive chemistry.
    "CHE_QUAL22": ("CHE_QUAL6", None),
    "CHEM_DESCRIPTIVE4": ("CHE_QUAL6",
        "Recall the characteristic flame-test colour produced by a given metal ion, such as golden yellow for sodium, brick red for calcium and lilac for potassium, and how the colour is observed."),
    # same explanation, two wordings, same topic and tier
    "CHE_QUAL7": ("CHE_QUAL4", None),
    # "balance a nuclear equation" extracted twice
    "CHEM_NUCLEAR10": ("CHEM_NUCLEAR0", None),
    # same limit technique, split across the limit and the derivative topics
    "MAT_CALC_DIFF5": ("MAT1_LIMIT4", None),
    # the squared case is not a separate competence from the unsquared one
    "MAT2_INVERSE_TRIG9": ("MAT2_INVERSE_TRIG0",
        "Calculate the value of a trigonometric function, or of its square, applied to an inverse trigonometric expression."),
    # two directions of one relation, both authored in the same batch
    "PHY2_PHOTOELECTRIC5": ("PHY2_PHOTOELECTRIC4",
        "Convert between the work function of a metal and its threshold frequency or threshold wavelength, in either direction."),
    # surfaced later, during review of the fragment-link proposals: the two
    # inverse-trig principal-value skills are the same fact, one a subset of the
    # other. Kept the superset.
    "MAT_INVTRIG4": ("MAT2_INVERSE_TRIG4", None),
}

# (child, parent) - the child is the subject that applies it, the parent the
# subject that teaches it first.
CROSS_SUBJECT = [
    ("MAT2_PLANE_MOTION0", "PHY1_KINEMATICS0"),
    ("MAT2_PLANE_MOTION1", "PHY1_KINEMATICS1"),
    ("MAT2_PLANE_MOTION2", "PHY1_KINEMATICS2"),
    ("MAT2_PLANE_MOTION3", "PHY1_KINEMATICS3"),
    ("MAT2_PLANE_MOTION4", "PHY1_KINEMATICS4"),
    ("MAT2_PLANE_MOTION9", "PHY1_NEWTON_LAWS4"),
    ("MAT2_PROJECTILE0", "PHY1_PROJECTILE0"),
    ("MAT2_PROJECTILE1", "PHY1_PROJECTILE1"),
    ("PHY1_VECTOR_PRODUCTS0", "MATH_MECH12"),
    ("PHY1_VECTOR_PRODUCTS1", "MATH_MECH16"),
]

# (Apply skill, the Remember skill it rests on)
TIER_EDGES = [
    ("CHE_ATOMIC9", "CHE_ATOMIC48"),
    ("CHE_ATOMIC40", "CHE_ATOMIC39"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    # already-merged losers are simply gone; skip them so this stays re-runnable
    for loser in [l for l in MERGES if l not in by_id]:
        del MERGES[loser]
    for loser, (winner, _) in MERGES.items():
        if winner not in by_id:
            sys.exit("ABORT: unknown winner %s" % winner)
        if by_id[loser]["subject"] != by_id[winner]["subject"]:
            sys.exit("ABORT: refusing to merge across subjects: %s / %s" % (loser, winner))
    for a, b in CROSS_SUBJECT + TIER_EDGES:
        for x in (a, b):
            if x not in by_id:
                sys.exit("ABORT: unknown skill %s" % x)

    remap = {l: w for l, (w, _) in MERGES.items()}

    # ---- rebuild the edge set with losers rewritten to winners ------------
    parents = collections.defaultdict(set)
    for child, plist in prereqs.items():
        c = remap.get(child, child)
        for p in plist:
            q = remap.get(p["id"], p["id"])
            if q != c:
                parents[c].add(q)
    for c, p in CROSS_SUBJECT + TIER_EDGES:
        parents[c].add(p)

    colour = collections.defaultdict(int)
    sys.setrecursionlimit(20000)

    def visit(n, stack):
        if colour[n] == 1:
            sys.exit("ABORT: cycle %s" % " -> ".join(stack + [n]))
        if colour[n] == 2:
            return
        colour[n] = 1
        for q in parents.get(n, ()):
            visit(q, stack + [n])
        colour[n] = 2

    for n in list(parents):
        visit(n, [])

    before = sum(len(v) for v in prereqs.values())
    after = sum(len(v) for v in parents.values())
    print("skills merged away : %d" % len(MERGES))
    print("cross-subject links: %d" % len(CROSS_SUBJECT))
    print("tier edges added   : %d" % len(TIER_EDGES))
    print("edges %d -> %d" % (before, after))
    print("no cycle           : OK")
    for loser, (winner, text) in MERGES.items():
        print("   %-22s -> %-22s%s" % (loser, winner, "  (winner reworded)" if text else ""))

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    for f in (TUPLES, PREREQS):
        shutil.copy2(f, BACKUP / (f.stem + ".pre_merge.json"))

    for _loser, (winner, text) in MERGES.items():
        if text:
            by_id[winner]["skillFull"] = text
    for a, b in CROSS_SUBJECT:
        by_id[a]["crossSubjectEquivalent"] = b
        by_id[b]["crossSubjectEquivalent"] = a

    tuples = [t for t in tuples if t["skillId"] not in remap]
    full_of = {t["skillId"]: t["skillFull"] for t in tuples}

    out = {}
    for child in sorted(parents):
        if child not in full_of:
            continue
        plist = [{"id": p, "full": full_of[p], "depth": 0}
                 for p in sorted(parents[child]) if p in full_of]
        if plist:
            out[child] = plist

    TUPLES.write_text(json.dumps(tuples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PREREQS.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nwrote tuples.json (%d skills), prereqs.json (%d edges)"
          % (len(tuples), sum(len(v) for v in out.values())))


if __name__ == "__main__":
    main()
