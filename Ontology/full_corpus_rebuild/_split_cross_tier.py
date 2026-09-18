"""Split the skills that fuse two Bloom tiers into one node.

WHY THIS MATTERS
----------------
`MasteryUpdater` assigns one guess/slip pair per skill, chosen from the skill's
Bloom level. A node that says "Recall X **and** write the equation for it" is two
skills wearing one id: a student who can do the first but not the second is
scored as though those were the same competence, and the DAG cannot express that
one leads to the other.

WHAT THIS IS NOT
----------------
`_cross_tier_skills.json` lists 47 candidates. Only **19** are split here. The
rest were re-read one by one and rejected, for three recurring reasons:

  - both halves sit at the same tier ("determine and name the shape",
    "calculate the ionic product and compare it with Ksp") - one skill, two
    sentences;
  - the second clause is an example or a gloss, not a second action
    ("define CFCs ... and write the structural formula of a named Freon");
  - the skill is a genuine Analyze task whose lower-tier half is a *prerequisite*
    rather than a component ("examine a set of configurations and identify the
    incorrect one"). Those get an edge instead - see EXTRA_EDGES.

This matches the earlier finding recorded at the top of `quality_audit.md`: the
regex that produced the candidate list over-flags by roughly half.

Idempotent: re-running detects the already-split text and makes no change.
`--dry-run` reports and writes nothing.
"""
import argparse
import collections
import json
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"
UNRESOLVED = HERE / "unresolved_prereqs.json"
BACKUP = HERE / "_prefix_backup"

# (original id, text the ORIGINAL keeps, bloom the ORIGINAL keeps,
#  text of the NEW skill, bloom of the NEW skill, direction)
# direction "new<-orig" : the new skill requires the original
# direction "orig<-new" : the original requires the new skill
SPLITS = [
    ("CHEM_DESCRIPTIVE21",
     "Recall that amphoteric metals such as lead, zinc and aluminium react with hot alkali to liberate hydrogen gas.", "Remember",
     "Write the balanced equation for the reaction of an amphoteric metal with hot alkali.", "Apply", "new<-orig"),
    ("CHEM_DESCRIPTIVE23",
     "Recall that water gas is produced by passing steam over red-hot coke.", "Remember",
     "Write the balanced equation for the production of water gas from steam and red-hot coke.", "Apply", "new<-orig"),
    ("CHEM_REDOX41",
     "Recall the definition of the electrochemical equivalent of an element as the mass liberated by one coulomb of charge.", "Remember",
     "Calculate the electrochemical equivalent of an element from its molar mass and the charge on its ion.", "Apply", "new<-orig"),
    ("CHEM_REDOX42",
     "Recall that one faraday is the charge carried by one mole of electrons, about 96500 coulombs.", "Remember",
     "Determine the number of faradays required to deposit or liberate a stated amount of a substance at an electrode.", "Apply", "new<-orig"),
    ("CHE_ORGANIC50",
     "Recall the definition of saponification as the alkaline hydrolysis of a fat or oil to give soap and glycerol.", "Remember",
     "Write the equation for the saponification of a named glyceride with sodium or potassium hydroxide.", "Apply", "new<-orig"),
    ("CHE_ORGANIC61",
     "Recall that formalin is a 30 to 40 per cent aqueous solution of methanal, and that it is used to preserve biological tissue.", "Remember",
     "Explain why a little alcohol is added to formalin, namely to stop the methanal polymerising to paraformaldehyde.", "Understand", "new<-orig"),
    ("CHE_STOICHIOMETRY31",
     "Recall the definition of normality as the number of gram-equivalents of solute per litre of solution.", "Remember",
     "Convert between the normality and the molarity of a solution using its equivalence factor.", "Apply", "new<-orig"),
    ("CHEM_PERIODIC31",
     "Recall the periodic trend that electronegativity increases across a period and decreases down a group.", "Remember",
     "Identify the most or the least electronegative element in a given set by applying the periodic trend.", "Apply", "new<-orig"),
    ("CHEM_STEREO3",
     "Explain that optical isomerism requires a carbon atom carrying four different groups.", "Understand",
     "Determine whether a given compound is optically active by testing its carbon atoms for chirality.", "Apply", "new<-orig"),
    ("CHEM_STEREO6",
     "Explain tautomerism as the dynamic equilibrium between the keto and the enol form of a carbonyl compound.", "Understand",
     "Identify which of a set of carbonyl compounds can show keto-enol tautomerism.", "Apply", "new<-orig"),
    ("CHE_ATOMIC62",
     "Explain why an atom or ion with a half-filled or a fully-filled p or d subshell has extra stability.", "Understand",
     "Compare the successive ionisation energies of related elements using the extra stability of half-filled and fully-filled subshells.", "Apply", "new<-orig"),
    ("CHE_ORGANIC84",
     "Explain how the oxy-acetylene flame is produced by burning ethyne in excess oxygen, and recall the approximate temperature it reaches.", "Understand",
     "Write the balanced equation for the complete combustion of ethyne in oxygen.", "Apply", "new<-orig"),
    ("CHE_ORGANIC113",
     "Explain the iodoform test, in which iodine and alkali give a yellow precipitate of iodoform.", "Understand",
     "Determine which compounds give a positive iodoform test, namely those containing a methyl ketone or a CH3CH(OH) group.", "Apply", "new<-orig"),
    ("CHE_ORGANIC122",
     "Write the dehydration of an alcohol to an alkene over heated alumina.", "Apply",
     "Recall that phosphoric acid gives a purer alkene than concentrated sulfuric acid when an alcohol is dehydrated.", "Remember", "new<-orig"),
    ("CHE_ORGANIC30",
     "Write the diazo-coupling reaction of a benzenediazonium salt with a phenol or an aromatic amine to form an azo dye.", "Apply",
     "Recall the name of the azo dye formed by coupling a benzenediazonium salt with a named phenol or aromatic amine.", "Remember", "new<-orig"),

    # these four read the other way round: the lower tier is the prerequisite
    ("CHE_ORGANIC66",
     "Write the conversion of ammonium cyanate to urea on heating.", "Apply",
     "Recall that the conversion of ammonium cyanate to urea is a rearrangement, and that this Wohler synthesis was the first preparation of an organic compound from an inorganic one.", "Remember", "orig<-new"),
    ("CHE_ORGANIC108",
     "Distinguish the SN1 and the SN2 substitution mechanisms by their rate-determining step and their stereochemical outcome.", "Understand",
     "Recall that the order of SN1 reactivity of the alkyl halides is tertiary greater than secondary greater than primary.", "Remember", "orig<-new"),
    ("CHE_ORGANIC109",
     "Predict the anti-Markovnikov product formed when a hydrogen halide adds to an alkene in the presence of a peroxide.", "Apply",
     "Explain the anti-Markovnikov orientation of peroxide-catalysed addition in terms of the free-radical mechanism and the stability of the radical formed.", "Understand", "orig<-new"),
    ("CHEM_ENV13",
     "Write the sequence of reactions by which atmospheric nitrogen is fixed during a lightning discharge, from N2 through NO and NO2 to nitric acid and nitrate salts.", "Apply",
     "Explain why the high temperature of a lightning discharge is what allows atmospheric nitrogen to react with oxygen.", "Understand", "orig<-new"),

    # raised separately: CHEM_AT1's own unresolved prerequisite asked for
    # exactly the Remember half of itself.
    ("CHEM_AT1",
     "Apply the Aufbau principle, the Pauli exclusion principle and Hund's rule to write the full ground-state electron configuration of an atom.", "Apply",
     "Recall the Aufbau principle, the Pauli exclusion principle and Hund's rule as the three rules governing the filling of atomic orbitals.", "Remember", "orig<-new"),
]

# Candidates that are genuinely one skill but were missing the prerequisite that
# their lower tier represents. An edge, not a split.
EXTRA_EDGES = [
    ("CHE_ATOMIC12", "CHE_ATOMIC11"),
    ("CHE_ATOMIC19", "CHE_ATOMIC17"),
    ("CHE_ATOMIC45", "CHE_ATOMIC17"),
    ("CHEM_REDOX39", "CHE2_MOLE2"),
    ("CHE_ACIDBASE55", "CHE_ACIDBASE27"),
    ("CHEM_NUCLEAR11", "CHEM_NUCLEAR0"),
]

# The last unresolved prerequisite in the file, authored here because it is the
# missing lower tier of CHE_QUAL7 rather than a topic gap.
AUTHORED = [
    ("CHE1_CATION_ANALYSIS", "Remember",
     "Recall that adding a strong acid to a sulfide-containing solution suppresses the ionisation of hydrogen sulfide and so lowers the sulfide-ion concentration.",
     "CHE_QUAL7"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    for sid, *_ in SPLITS:
        if sid not in by_id:
            sys.exit("ABORT: unknown skill %s" % sid)
    for a, b in EXTRA_EDGES:
        for x in (a, b):
            if x not in by_id:
                sys.exit("ABORT: unknown skill in EXTRA_EDGES: %s" % x)

    maxsuf = collections.defaultdict(lambda: -1)
    for t in tuples:
        m = re.match(r"^(.*[^0-9])(\d+)$", t["skillId"])
        if m:
            maxsuf[m.group(1)] = max(maxsuf[m.group(1)], int(m.group(2)))

    new_rows, new_edges, rewrites = [], [], []

    def mint(topic):
        maxsuf[topic] += 1
        sid = "%s%d" % (topic, maxsuf[topic])
        if sid in by_id:
            sys.exit("ABORT: minted id collides: %s" % sid)
        return sid

    for sid, orig_text, orig_bloom, new_text, new_bloom, direction in SPLITS:
        t = by_id[sid]
        if t["skillFull"] == orig_text:
            continue  # already split on a previous run
        topic = t["topicKey"]
        nid = mint(topic)
        rewrites.append((sid, t["skillFull"], orig_text, t["bloom"], orig_bloom))
        new_rows.append({
            "bloom": new_bloom, "skillId": nid, "skillFull": new_text,
            "topicKey": topic, "topicLabel": t["topicLabel"],
            "subject": t["subject"], "splitFrom": sid,
        })
        new_edges.append((nid, sid) if direction == "new<-orig" else (sid, nid))

    for topic, bloom, text, requirer in AUTHORED:
        if any(t["skillFull"] == text for t in tuples):
            continue
        nid = mint(topic)
        ref = by_id[requirer]
        new_rows.append({
            "bloom": bloom, "skillId": nid, "skillFull": text,
            "topicKey": topic, "topicLabel": ref["topicLabel"],
            "subject": ref["subject"], "authored": True,
        })
        new_edges.append((requirer, nid))

    new_edges.extend(EXTRA_EDGES)

    # cycle check over the resulting graph
    parents = collections.defaultdict(set)
    for k, v in prereqs.items():
        for p in v:
            parents[k].add(p["id"])
    for c, p in new_edges:
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

    print("splits applied : %d" % len(rewrites))
    print("skills authored: %d" % (len(new_rows) - len(rewrites)))
    print("new edges      : %d" % len(new_edges))
    print("no cycle       : OK")
    for sid, old, new, ob, nb in rewrites:
        print("\n  %s  [%s -> %s]" % (sid, ob, nb))
        print("    was : %s" % old[:120])
        print("    now : %s" % new[:120])

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    for f in (TUPLES, PREREQS, UNRESOLVED):
        shutil.copy2(f, BACKUP / (f.stem + ".pre_split.json"))

    for sid, _old, new_text, _ob, new_bloom in rewrites:
        by_id[sid]["skillFull"] = new_text
        by_id[sid]["bloom"] = new_bloom
    tuples.extend(new_rows)

    full_of = {t["skillId"]: t["skillFull"] for t in tuples}
    for c, p in new_edges:
        bucket = prereqs.setdefault(c, [])
        if not any(x["id"] == p for x in bucket):
            bucket.append({"id": p, "full": full_of[p], "depth": 0})
    # split descriptions changed, so refresh every cached 'full'
    for child, plist in prereqs.items():
        for p in plist:
            if p["id"] in full_of:
                p["full"] = full_of[p["id"]]

    TUPLES.write_text(json.dumps(tuples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PREREQS.write_text(json.dumps(prereqs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    unresolved = json.loads(UNRESOLVED.read_text(encoding="utf-8"))
    for k in ("CHEM_AT1", "CHE_QUAL7"):
        unresolved.pop(k, None)
    UNRESOLVED.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nwrote tuples.json, prereqs.json, unresolved_prereqs.json")
    print("unresolved remaining: %d" % len(unresolved))


if __name__ == "__main__":
    main()
