"""Fixes for the findings raised by `_validate_ontology.py`.

WHAT WAS AND WAS NOT TREATED AS A DEFECT
----------------------------------------
The validator's first run flagged 147 "Bloom inversions" - edges whose
prerequisite sits at a higher Bloom tier than the skill requiring it. Reading
them one by one, almost all are **correct**, and the check was the thing that
was wrong:

    MAT_MATRIX16 (Remember: a determinant with two equal rows is zero)
        requires MAT_MATRIX13 (Apply: evaluate a 3x3 determinant)

That is exactly the right order. A low-tier *fact about* an operation is learned
after the operation itself. Bloom tier measures cognitive demand, not teaching
sequence, and the two are independent. The check is therefore downgraded to a
review list in the validator rather than being "fixed" in the data.

Three edges in that list were genuinely wrong and are corrected here, plus a
misfiled skill, the four isolated skills, the topics with no internal learning
order, and the topics left holding a single skill.
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
CONFIG = REPO / "Backend" / "tree_data" / "ontology_config.json"
BACKUP = HERE / "_prefix_backup"

# --- edges to delete -------------------------------------------------------
DROP = [
    # authored in _author_foundations.py and wrong: recalling the NAMES of the
    # reaction types does not depend on being able to balance an equation.
    ("CHE2_MOLE3", "CHE2_MOLE2"),
    # left behind by the CHE_ORGANIC50 split. The original said "define
    # saponification AND write the equation"; the esterification prerequisite
    # belongs to the writing half, which is now CHE2_ORG_ACID0.
    ("CHE_ORGANIC50", "CHE_ORGANIC47"),
]

# --- edges to add ----------------------------------------------------------
ADD = [
    # the two re-pointings for the drops above
    ("CHE_STOICHIOMETRY3", "CHE2_MOLE3"),
    ("CHE2_ORG_ACID0", "CHE_ORGANIC47"),
    # Faraday's first law uses the electrochemical equivalent, so it needs the
    # half of CHEM_REDOX41 that actually computes one
    ("CHEM_REDOX40", "CHE1_REDOX6"),

    # --- grounding higher-tier skills that had no prerequisite at all -------
    ("CHE_ACIDBASE15", "CHE_ACIDBASE43"),
    ("CHE_ACIDBASE15", "CHE_ACIDBASE50"),
    ("CHE_ACIDBASE18", "CHE_ACIDBASE50"),
    ("CHE_ACIDBASE19", "CHE_STOICHIOMETRY31"),
    ("CHE_ACIDBASE32", "CHE_ACIDBASE43"),
    ("CHE_ATOMIC22", "CHE_ATOMIC49"),
    # NOT grounded: CHE_ATOMIC25 (E = hc/lambda) is already an ancestor of
    # CHEM_SPEC3 through CHEM_SPEC4, so grounding it there would close a cycle.
    # It is a legitimate root - the Planck relation rests on nothing else here.
    ("CHEM_SPEC8", "CHEM_SPEC3"),
    ("CHE_BONDING50", "CHE1_COVALENT_BOND0"),
    ("CHE_BONDING8", "CHE_BONDING27"),
    ("CHE_BONDING39", "CHE_BONDING27"),
    ("CHE_BONDING37", "CHE1_COVALENT_BOND1"),
    # NOT grounded: CHE_BONDING30 is already the prerequisite of CHE_BONDING25,
    # so the obvious-looking edge would close a two-cycle. It is a legitimate
    # root of the intermolecular-forces family.
    ("CHE_EQUILIBRIUM11", "CHE_EQUILIBRIUM30"),
    ("CHE_EQUILIBRIUM20", "CHE2_MOLE2"),
    ("CHE_EQUILIBRIUM26", "CHE_GASLAWS13"),
    ("CHEM_REDOX28", "CHE1_REDOX0"),
    ("CHEM_REDOX31", "CHE1_REDOX4"),
    ("CHEM_REDOX7", "CHE1_REDOX2"),
    ("CHE_THERMOCHEM1", "CHE_THERMOCHEM11"),
    ("CHE_THERMOCHEM19", "CHE_THERMOCHEM11"),
    ("CHE_THERMOCHEM4", "CHE_THERMOCHEM13"),
    ("CHE_ELECTROCHEM2", "CHE_ELECTROCHEM7"),
    ("CHE_ELECTROCHEM1", "CHE1_REDOX1"),
    ("CHE_ELECTROCHEM3", "CHE_ELECTROCHEM8"),
    ("CHEM_GAS1", "CHE_GASLAWS26"),
    ("CHE_GASLAWS17", "CHE_GASLAWS26"),
    ("CHE_GASLAWS18", "CHE_GASLAWS26"),
    ("CHE_STOICHIOMETRY11", "CHE2_MOLE0"),

    # --- isolated skills, given a home -------------------------------------
    ("CHEM_LAB14", "CHEM_LAB8"),
    # a sooty, luminous flame is the unsaturation test done by eye
    ("CHEM_LAB2", "CHE_ORGANIC137"),
    ("CHEM_SOLID2", "CHEM_SOLID5"),
    ("CHEM_NOM4", "CHEM_NOM13"),

    # --- topics that had no internal learning order ------------------------
    ("CHEM_DESCRIPTIVE16", "CHEM_DESCRIPTIVE14"),
    ("CHEM_LAB7", "CHEM_LAB1"),
    ("CHEM_LAB11", "CHEM_LAB1"),
    ("CHE_STOICHIOMETRY24", "CHE_STOICHIOMETRY23"),
    ("CHEM_ANALYTICAL15", "CHE_STOICHIOMETRY23"),
    ("MATH_MECH19", "MATH_MECH18"),
    ("MATH_MECH27", "MATH_MECH18"),
    ("PHY1_ENERGY_CONSERVATION0", "PHY1_ENERGY_CONSERVATION2"),
    ("PHY1_ENERGY_CONSERVATION1", "PHY1_ENERGY_CONSERVATION2"),
]

# --- a skill in the wrong topic -------------------------------------------
RETAG = {
    # "Recall the definition of an ore" was sitting in organic nomenclature
    "CHEM_NOM6": "CHE2_METALLURGY",
}

# --- skills authored to make single-skill topics teachable -----------------
# key, bloom, text, topicKey, subject
AUTHORED = [
    ("M1", "Remember", "Recall the meanings of ore, gangue and flux, and the difference between a mineral and an ore.", "CHE2_METALLURGY", "Chemistry"),
    ("M2", "Understand", "Distinguish roasting from calcination as preliminary treatments of an ore.", "CHE2_METALLURGY", "Chemistry"),
    ("M3", "Apply", "Determine the reducing agent and the method used to extract a stated metal from its ore.", "CHE2_METALLURGY", "Chemistry"),

    ("F1", "Remember", "Recall the laws of limiting friction and the meaning of the coefficient of friction.", "PHY1_FRICTION", "Physics"),
    ("F2", "Apply", "Calculate the frictional force acting on a body from the normal reaction and the coefficient of friction.", "PHY1_FRICTION", "Physics"),
    ("F3", "Apply", "Determine the angle of repose, or the angle of friction, for a body resting on an inclined plane.", "PHY1_FRICTION", "Physics"),

    ("G1", "Remember", "Recall the symbol and the truth table of the AND, the OR and the NOT gate.", "PHY2_LOGIC_GATES", "Physics"),
    ("G2", "Apply", "Determine the output of a combination of logic gates for every combination of its inputs.", "PHY2_LOGIC_GATES", "Physics"),
    ("G3", "Understand", "Explain why NAND and NOR are called universal gates.", "PHY2_LOGIC_GATES", "Physics"),

    ("H1", "Remember", "Recall that the total energy of a body in simple harmonic motion is constant and proportional to the square of its amplitude.", "PHY1_SHM_ENERGY", "Physics"),
    ("H2", "Apply", "Determine the displacement at which the kinetic and the potential energy of a body in simple harmonic motion are equal.", "PHY1_SHM_ENERGY", "Physics"),
]

AUTHORED_EDGES = [
    ("M2", "M1"), ("M3", "M2"), ("CHEM_DESCRIPTIVE3", "M1"), ("CHEM_NOM6", "M1"),
    ("F2", "F1"), ("F3", "F2"), ("PHY1_NEWTON_LAWS6", "F2"),
    ("G2", "G1"), ("G3", "G1"), ("PHY2_LOGIC_GATES0", "G1"),
    ("PHY1_SHM_ENERGY0", "H1"), ("H2", "PHY1_SHM_ENERGY0"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    labels = cfg["topic_labels"]
    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    maxsuf = collections.defaultdict(lambda: -1)
    for t in tuples:
        m = re.match(r"^(.*[^0-9])(\d+)$", t["skillId"])
        if m:
            maxsuf[m.group(1)] = max(maxsuf[m.group(1)], int(m.group(2)))

    minted = {}
    for key, bloom, text, topic, subject in AUTHORED:
        if any(t["skillFull"] == text for t in tuples):
            sys.exit("ABORT: already authored: %s" % text[:50])
        maxsuf[topic] += 1
        sid = "%s%d" % (topic, maxsuf[topic])
        if sid in by_id:
            sys.exit("ABORT: id collision %s" % sid)
        lab = labels[topic]
        minted[key] = {
            "bloom": bloom, "skillId": sid, "skillFull": text,
            "topicKey": topic,
            "topicLabel": lab if isinstance(lab, str) else lab.get("en", topic),
            "subject": subject, "authored": True,
        }

    def rid(ref):
        if ref in minted:
            return minted[ref]["skillId"]
        if ref in by_id:
            return ref
        sys.exit("ABORT: unknown reference %s" % ref)

    add = [(rid(a), rid(b)) for a, b in ADD + AUTHORED_EDGES]

    parents = collections.defaultdict(set)
    for c, v in prereqs.items():
        for p in v:
            parents[c].add(p["id"])
    for c, p in DROP:
        if p not in parents.get(c, ()):
            sys.exit("ABORT: edge to drop does not exist: %s <- %s" % (c, p))
        parents[c].discard(p)
    for c, p in add:
        if c == p:
            sys.exit("ABORT: self edge %s" % c)
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

    print("edges dropped : %d" % len(DROP))
    print("edges added   : %d" % len(add))
    print("skills authored: %d" % len(minted))
    print("skills retagged: %d" % len(RETAG))
    print("no cycle      : OK")

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    for f in (TUPLES, PREREQS):
        shutil.copy2(f, BACKUP / (f.stem + ".pre_valfix.json"))

    for sid, topic in RETAG.items():
        lab = labels[topic]
        by_id[sid]["topicKey"] = topic
        by_id[sid]["topicLabel"] = lab if isinstance(lab, str) else lab.get("en", topic)
    tuples.extend(minted[k] for k, *_ in AUTHORED)

    full_of = {t["skillId"]: t["skillFull"] for t in tuples}
    out = {}
    for c in sorted(parents):
        if c not in full_of:
            continue
        plist = [{"id": p, "full": full_of[p], "depth": 0}
                 for p in sorted(parents[c]) if p in full_of]
        if plist:
            out[c] = plist

    TUPLES.write_text(json.dumps(tuples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PREREQS.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nwrote tuples.json (%d skills), prereqs.json (%d edges)"
          % (len(tuples), sum(len(v) for v in out.values())))


if __name__ == "__main__":
    main()
