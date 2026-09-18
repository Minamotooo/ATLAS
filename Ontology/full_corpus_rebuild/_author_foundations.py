"""Author the foundational skills the corpus never taught, and wire them in.

WHY THIS EXISTS
---------------
Two problems with one cause.

1. Three syllabus topics still had no skills after `_retag_topics.py`:
   `MAT2_EXPONENTIAL_EQ`, `PHY1_ERRORS` and `PHY1_SOLID_BONDING`. A corpus-wide
   search confirms the source books contain no exercises on them - they are
   assumed knowledge carried up from SSC, so nothing was there to extract.

2. `unresolved_prereqs.json` held 46 prerequisite mentions that the extraction
   asked for and no skill satisfied. Reading them, most name exactly the same
   assumed knowledge: "solve a linear equation", "evaluate a logarithm",
   "calculate a molar mass", "balance a chemical equation", "recall the VSEPR
   postulate". The corpus never drills these because every HSC question takes
   them for granted - but the DAG needs them, because they are what the rest of
   the graph hangs from.

So these are authored rather than extracted. Each one is deliberately a root or
near-root: short, single-action, and genuinely prerequisite to the skills that
asked for it. They carry no `sourceItemIds` because no corpus item teaches them,
which is also how you can tell them apart from extracted skills later.

SAFETY
------
- refuses to write if an id it mints already exists;
- refuses to write if an edge would close a cycle;
- refuses to write if a referring skillId does not exist;
- backs up tuples/prereqs/unresolved before writing;
- `--dry-run` reports and writes nothing.
"""
import argparse
import json
import pathlib
import re
import shutil
import sys
import collections

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
TUPLES = HERE / "tuples.json"
PREREQS = HERE / "prereqs.json"
UNRESOLVED = HERE / "unresolved_prereqs.json"
CONFIG = REPO / "Backend" / "tree_data" / "ontology_config.json"
BACKUP = HERE / "_prefix_backup"

S = "Chemistry"
M = "Mathematics"
P = "Physics"

# key, bloom, description, topicKey, subject
NEW = [
    # --- MAT2_EXPONENTIAL_EQ: was empty; also the target of 4 unresolved refs
    ("E1", "Remember", "Recall the laws of logarithms and the equivalence between a logarithm and its exponential form.", "MAT2_EXPONENTIAL_EQ", M),
    ("E2", "Apply", "Evaluate a common (base-10) logarithm or antilogarithm of a given positive number.", "MAT2_EXPONENTIAL_EQ", M),
    ("E3", "Apply", "Evaluate a natural logarithm or an exponential expression.", "MAT2_EXPONENTIAL_EQ", M),
    ("E4", "Apply", "Solve an equation in which the unknown appears as an exponent, by taking logarithms of both sides.", "MAT2_EXPONENTIAL_EQ", M),
    ("E5", "Apply", "Solve a logarithmic equation by rewriting it in exponential form.", "MAT2_EXPONENTIAL_EQ", M),

    # --- MAT2_POLYNOMIAL: had only root-coefficient relations, so its label
    #     ("Polynomials and the Remainder Theorem") described content that did
    #     not exist. P4/P5 supply it; P1-P3 are the assumed algebra that four
    #     Chemistry skills asked for.
    ("P1", "Apply", "Solve a linear equation in one unknown by rearranging and simplifying its terms.", "MAT2_POLYNOMIAL", M),
    ("P2", "Apply", "Rearrange a multi-variable formula to make a stated variable its subject.", "MAT2_POLYNOMIAL", M),
    ("P3", "Apply", "Solve a quadratic equation by factorisation or by the quadratic formula, and select the physically valid root.", "MAT2_POLYNOMIAL", M),
    ("P4", "Remember", "Recall the remainder theorem and the factor theorem for a polynomial.", "MAT2_POLYNOMIAL", M),
    ("P5", "Apply", "Determine the remainder on division, or verify a factor, of a polynomial using the remainder and factor theorems.", "MAT2_POLYNOMIAL", M),

    # --- PHY1_ERRORS: was empty
    ("R1", "Remember", "Recall the distinction between systematic and random error, and between the precision and the accuracy of a measurement.", "PHY1_ERRORS", P),
    ("R2", "Apply", "Determine the least count of a measuring instrument and express a reading to the corresponding number of significant figures.", "PHY1_ERRORS", P),
    ("R3", "Apply", "Calculate the absolute, the relative and the percentage error of a measured quantity.", "PHY1_ERRORS", P),
    ("R4", "Apply", "Convert a physical quantity from one system of units to another.", "PHY1_ERRORS", P),

    # --- PHY1_SOLID_BONDING: was empty
    ("S1", "Remember", "Recall the four principal types of bonding found in solids - ionic, covalent, metallic and molecular - and the properties each confers.", "PHY1_SOLID_BONDING", P),
    ("S2", "Understand", "Distinguish a crystalline solid from an amorphous one by the order of the arrangement of its particles.", "PHY1_SOLID_BONDING", P),
    ("S3", "Understand", "Relate a mechanical property of a solid, such as its hardness or its ductility, to the bonding between its particles.", "PHY1_SOLID_BONDING", P),

    # --- Chemistry foundations that the corpus assumes -----------------------
    ("C1", "Apply", "Calculate the molar mass of a compound by summing the atomic masses of the elements in its formula.", "CHE2_MOLE", S),
    ("C2", "Apply", "Calculate a percentage composition from a mass ratio.", "CHE2_MOLE", S),
    ("C8", "Apply", "Balance a chemical equation by adjusting its stoichiometric coefficients so that every element is conserved.", "CHE2_MOLE", S),
    ("C9", "Remember", "Recall the common reaction types - combination, decomposition, displacement, double displacement and neutralisation.", "CHE2_MOLE", S),

    ("C3", "Remember", "Recall the definitions of oxidation and of reduction, in terms of electron loss and gain and of oxygen and hydrogen transfer.", "CHE1_REDOX", S),
    ("C4", "Remember", "Recall the definitions of an oxidising agent and of a reducing agent.", "CHE1_REDOX", S),
    ("C5", "Remember", "Recall the rules for assigning oxidation numbers, including the usual values taken by oxygen and by hydrogen.", "CHE1_REDOX", S),
    ("C6", "Remember", "Recall the definition of a disproportionation reaction.", "CHE1_REDOX", S),
    ("C7", "Remember", "Recall the reactivity series of the metals and what it predicts about displacement reactions.", "CHE1_REDOX", S),
    ("C21", "Remember", "Recall that concentrated nitric acid is a strong oxidising acid that attacks most metals and several non-metals.", "CHE1_REDOX", S),

    ("C10", "Remember", "Recall the basic postulate of VSEPR theory, that the electron pairs around a central atom arrange themselves so as to minimise repulsion.", "CHE1_COVALENT_BOND", S),
    ("C11", "Remember", "Recall the definition of a coordinate (dative) covalent bond, in which both shared electrons come from one atom.", "CHE1_COVALENT_BOND", S),
    ("C12", "Remember", "Recall the molecular-orbital energy-level filling order for the period-2 diatomic molecules.", "CHE1_COVALENT_BOND", S),

    ("C13", "Remember", "Recall the distinction between ionic and covalent bonding character and the electronegativity difference that separates them.", "CHE1_IONIC_BOND", S),
    ("C14", "Remember", "Recall the radius-ratio rule and the coordination numbers it predicts for an ionic crystal.", "CHE1_IONIC_BOND", S),

    ("C15", "Remember", "Recall the periodic trends in atomic and ionic radius across a period and down a group.", "CHE1_PERIODIC_TRENDS", S),
    ("C16", "Remember", "Recall that metal oxides are generally basic and non-metal oxides generally acidic.", "CHE1_PERIODIC_TRENDS", S),
    ("C17", "Remember", "Recall that period-3 and later elements have energetically accessible d orbitals and can therefore expand their octet.", "CHE1_PERIODIC_TRENDS", S),
    ("C22", "Remember", "Recall that the strength of pi (multiple) bonding falls off down a group.", "CHE1_PERIODIC_TRENDS", S),
    ("C23", "Remember", "Recall the trend from ionic through polar covalent to covalent bonding on crossing a period.", "CHE1_PERIODIC_TRENDS", S),

    ("C18", "Remember", "Recall the 'like dissolves like' principle relating the polarity of a solvent to the solubility of a solute.", "CHE1_SOLUBILITY_RULES", S),
    ("C19", "Remember", "Recall the solubility of the silver halides in dilute and in concentrated ammonia.", "CHE1_SOLUBILITY_RULES", S),

    ("C20", "Remember", "Recall the common oxidation states exhibited by the first-row transition metals.", "CHE1_TRANSITION", S),
]

# child requires parent, both among the newly authored skills
INTERNAL = [
    ("E2", "E1"), ("E3", "E1"), ("E4", "E1"), ("E4", "E3"), ("E5", "E1"),
    ("P2", "P1"), ("P3", "P1"), ("P5", "P4"),
    ("R2", "R1"), ("R3", "R1"), ("R3", "R2"), ("R4", "R2"),
    ("S2", "S1"), ("S3", "S1"),
    ("C2", "C1"), ("C8", "C1"), ("C9", "C8"),
    ("C4", "C3"), ("C5", "C3"), ("C6", "C5"), ("C7", "C3"), ("C21", "C4"),
    ("C12", "C10"), ("C11", "C13"), ("C14", "C13"), ("C13", "C15"),
    ("C16", "C15"), ("C17", "C15"), ("C22", "C15"), ("C23", "C15"),
    ("C18", "C13"), ("C19", "C18"), ("C20", "C15"),
]

# existing skill -> the prerequisite it was asking for.
# A bare key like "C1" names a newly authored skill; anything else is an
# existing skillId that already satisfied the request and only needed linking.
RESOLVE = {
    "CHE_ATOMIC29": ["P1"],
    "CHE_EQUILIBRIUM6": ["P3"],
    "CHE_GASLAWS5": ["P2"],
    "CHE_EQUILIBRIUM18": ["E4"],
    "CHE_ACIDBASE23": ["E2"],
    "CHEM_KIN4": ["E3"],
    "CHEM_KIN5": ["E3"],
    "CHEM_NUCLEAR3": ["R4"],
    "CHEM_DESCRIPTIVE0": ["C8"],
    "CHE_STOICHIOMETRY5": ["C1"],
    "CHE_STOICHIOMETRY10": ["C1"],
    "CHE_STOICHIOMETRY12": ["C1"],
    "CHE_STOICHIOMETRY7": ["C2"],
    "CHEM_REDOX23": ["C3"],
    "CHEM_REDOX11": ["C4"],
    "CHEM_REDOX2": ["C5"],
    "CHEM_REDOX14": ["C6"],
    "CHEM_REDOX13": ["C7"],
    "CHEM_REDOX12": ["C9"],
    "CHEM_REDOX17": ["C21"],
    "CHE_BONDING19": ["C10"],
    "CHE_BONDING20": ["C10"],
    "CHE_BONDING16": ["C11"],
    "CHE_COORD5": ["C11"],
    "CHE_COORD6": ["C11"],
    "CHE_BONDING35": ["C12"],
    "CHE_ACIDBASE3": ["C13"],
    "CHE_BONDING38": ["C14"],
    "CHE_ACIDBASE7": ["C15"],
    "CHEM_PERIODIC15": ["C15"],
    "CHE_ACIDBASE8": ["C16"],
    "CHE_BONDING15": ["C17"],
    "CHE_BONDING51": ["C22"],
    "CHE_BONDING32": ["C23"],
    "CHE_BONDING34": ["C23"],
    "CHEM_LAB10": ["C18"],
    "CHE_QUAL9": ["C19"],
    "CHE_COORD9": ["C20"],
    # already satisfied by an existing skill - these only needed the link
    "CHE_EQUILIBRIUM9": ["CHE_ACIDBASE15"],
    "CHE_ATOMIC50": ["CHE_ATOMIC23"],
    "CHE_QUAL13": ["CHE_QUAL19"],
    "CHE_QUAL16": ["CHE_QUAL11"],
    "CHE_BONDING31": ["CHE_BONDING20"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    labels = cfg["topic_labels"]
    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    # ---- mint ids ---------------------------------------------------------
    maxsuf = collections.defaultdict(lambda: -1)
    for t in tuples:
        m = re.match(r"^(.*[^0-9])(\d+)$", t["skillId"])
        if m:
            maxsuf[m.group(1)] = max(maxsuf[m.group(1)], int(m.group(2)))

    minted = {}
    for key, bloom, full, topic, subject in NEW:
        if topic not in labels:
            sys.exit("ABORT: unknown topic %s" % topic)
        maxsuf[topic] += 1
        sid = "%s%d" % (topic, maxsuf[topic])
        if sid in by_id:
            sys.exit("ABORT: minted id already exists: %s" % sid)
        lab = labels[topic]
        minted[key] = {
            "bloom": bloom,
            "skillId": sid,
            "skillFull": full,
            "topicKey": topic,
            "topicLabel": lab if isinstance(lab, str) else lab.get("en", topic),
            "subject": subject,
            "authored": True,
        }

    def resolve(ref):
        if ref in minted:
            return minted[ref]["skillId"]
        if ref in by_id:
            return ref
        sys.exit("ABORT: unknown reference %r" % ref)

    # ---- assemble edges ---------------------------------------------------
    new_edges = []  # (child, parent)
    for child, parent in INTERNAL:
        new_edges.append((resolve(child), resolve(parent)))
    for child, refs in RESOLVE.items():
        if child not in by_id:
            sys.exit("ABORT: referring skill does not exist: %s" % child)
        for r in refs:
            new_edges.append((child, resolve(r)))

    # ---- cycle check on the combined graph --------------------------------
    parents = collections.defaultdict(set)
    for k, v in prereqs.items():
        for p in v:
            parents[k].add(p["id"])
    for c, p in new_edges:
        parents[c].add(p)

    WHITE, GREY, BLACK = 0, 1, 2
    colour = collections.defaultdict(int)

    def visit(n, stack):
        if colour[n] == GREY:
            sys.exit("ABORT: cycle %s" % " -> ".join(stack + [n]))
        if colour[n] == BLACK:
            return
        colour[n] = GREY
        for q in parents.get(n, ()):
            visit(q, stack + [n])
        colour[n] = BLACK

    sys.setrecursionlimit(10000)
    for n in list(parents):
        visit(n, [])

    print("new skills   : %d" % len(minted))
    print("new edges    : %d  (%d internal, %d resolving)"
          % (len(new_edges), len(INTERNAL), len(new_edges) - len(INTERNAL)))
    print("no cycle     : OK")
    by_topic = collections.Counter(v["topicKey"] for v in minted.values())
    for k, n in sorted(by_topic.items()):
        print("    %-24s +%d" % (k, n))

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    for f in (TUPLES, PREREQS, UNRESOLVED):
        shutil.copy2(f, BACKUP / (f.stem + ".pre_foundations.json"))

    tuples.extend(minted[k] for k, *_ in NEW)
    full_of = {t["skillId"]: t["skillFull"] for t in tuples}
    for c, p in new_edges:
        bucket = prereqs.setdefault(c, [])
        if not any(x["id"] == p for x in bucket):
            bucket.append({"id": p, "full": full_of[p], "depth": 0})

    TUPLES.write_text(json.dumps(tuples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PREREQS.write_text(json.dumps(prereqs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    unresolved = json.loads(UNRESOLVED.read_text(encoding="utf-8"))
    for k in list(unresolved):
        if k in RESOLVE:
            del unresolved[k]
    UNRESOLVED.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nwrote tuples.json, prereqs.json, unresolved_prereqs.json")
    print("unresolved skills remaining: %d" % len(unresolved))


if __name__ == "__main__":
    main()
