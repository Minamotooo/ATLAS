"""
_apply_bloom_fixes.py
---------------------
Fix the 68 skills whose leading action verb contradicts their assigned Bloom
level (see `quality_audit.md` Finding 2).

Every decision is in DECISIONS below — one entry per skill, hand-classified.
Two kinds:

    ("bloom", NewLevel)
        The described cognitive work does not match the level that was assigned.
        The LEVEL is corrected. These change engine behaviour: `MasteryUpdater`
        picks BKT guess/slip parameters from the Bloom level, so a wrong level
        means a wrong update size per answer.

    ("text", old_fragment, new_fragment)
        The level is right; the wording opened with a verb from the wrong Bloom
        row. The DESCRIPTION is reworded so its verb agrees with the level, per
        the rule in `ontology_rebuild_system_prompt.md` Global Constraint 1
        ("the description is wrong - rewrite it, don't relabel the level").
        No engine effect; this keeps the data self-consistent for future batches.

Run from the repo root:
    python Ontology/full_corpus_rebuild/_apply_bloom_fixes.py --dry-run
    python Ontology/full_corpus_rebuild/_apply_bloom_fixes.py --apply

Originals are in `_prefix_backup/`. Nothing else is touched; prereqs.json is not
modified (no skillIds change).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# skillId -> ("bloom", level) | ("text", old, new)
DECISIONS: dict[str, tuple] = {
    # ---- level is wrong: recall of a stored fact, not a procedure -------------
    "CHEM_DESCRIPTIVE13": ("bloom", "Remember"),
    "CHEM_ENV28":         ("bloom", "Remember"),
    "CHEM_GASLAW3":       ("bloom", "Remember"),
    "CHEM_LAB13":         ("bloom", "Remember"),
    "CHE_ATOMIC59":       ("bloom", "Remember"),
    "CHE_COORD3":         ("bloom", "Remember"),
    "CHE_ORGANIC100":     ("bloom", "Remember"),
    "CHE_ORGANIC111":     ("bloom", "Remember"),
    "CHE_ORGANIC136":     ("bloom", "Remember"),
    "CHE_ORGANIC50":      ("bloom", "Remember"),
    "CHE_ORGANIC76":      ("bloom", "Remember"),

    # ---- level is wrong: explanatory/contrastive work, not recall or procedure -
    "CHEM_ANALYTICAL11":  ("bloom", "Understand"),
    "CHEM_SOLUTION10":    ("bloom", "Understand"),
    "CHE_ACIDBASE13":     ("bloom", "Understand"),
    "CHE_ACIDBASE46":     ("bloom", "Understand"),
    "CHE_ACIDBASE47":     ("bloom", "Understand"),
    "CHE_ACIDBASE8":      ("bloom", "Understand"),
    "CHE_BONDING34":      ("bloom", "Understand"),
    "CHE_ORGANIC31":      ("bloom", "Understand"),

    # ---- level is wrong: applying a rule/procedure to a new case --------------
    "CHEM_KIN28":         ("bloom", "Apply"),
    "CHEM_LAB10":         ("bloom", "Apply"),
    "CHEM_PERIODIC4":     ("bloom", "Apply"),
    "CHEM_REDOX13":       ("bloom", "Apply"),
    "CHE_ACIDBASE44":     ("bloom", "Apply"),
    "CHE_ACIDBASE57":     ("bloom", "Apply"),
    "CHE_ACIDBASE58":     ("bloom", "Apply"),
    "CHE_ATOMIC13":       ("bloom", "Apply"),
    "CHE_BONDING29":      ("bloom", "Apply"),
    "CHE_BONDING56":      ("bloom", "Apply"),
    "CHE_EQUILIBRIUM16":  ("bloom", "Apply"),
    "CHE_ORGANIC151":     ("bloom", "Apply"),
    "CHE_STOICHIOMETRY34": ("bloom", "Apply"),

    # ---- level is wrong: breaking evidence apart to reach a conclusion --------
    "CHEM_NUCLEAR11":     ("bloom", "Analyze"),
    "CHE_ORGANIC110":     ("bloom", "Analyze"),
    "CHE_ORGANIC116":     ("bloom", "Analyze"),
    "CHE_ORGANIC157":     ("bloom", "Analyze"),

    # ---- level is right, verb was imprecise: Identify -> Determine (Apply) ----
    "CHE_ATOMIC2":   ("text", "Identify the element corresponding",
                              "Determine the element corresponding"),
    "CHE_ATOMIC50":  ("text", "Identify the initial and final principal quantum numbers",
                              "Determine the initial and final principal quantum numbers"),
    "CHE_ATOMIC61":  ("text", "Identify an element from its period number",
                              "Determine an element from its period number"),
    "CHE_BONDING14": ("text", "Identify the specific atomic orbitals",
                              "Determine the specific atomic orbitals"),
    "CHE_BONDING23": ("text", "Identify which type of orbital overlap",
                              "Determine which type of orbital overlap"),
    "CHE_BONDING37": ("text", "Identify which of several given compounds or ions",
                              "Determine which of several given compounds or ions"),
    "CHE_QUAL3":     ("text", "Identify an unknown ion present in a solution",
                              "Determine an unknown ion present in a solution"),

    # ---- level is right, verb was imprecise: Compare -> Determine (Apply) -----
    "CHEM_PERIODIC15": ("text", "Compare the atomic radii of elements",
                                "Determine the relative atomic radii of elements"),
    "CHE_BONDING26":   ("text", "Compare the lengths of different covalent bonds",
                                "Determine the relative lengths of different covalent bonds"),
    "CHE_BONDING32":   ("text", "Compare the melting points of a series of period-3 chlorides",
                                "Determine the relative melting points of a series of period-3 chlorides"),
    "CHE_BONDING33":   ("text", "Compare bond angles across a series of related molecules",
                                "Determine the relative bond angles across a series of related molecules"),
    "CHE_GASLAWS41":   ("text", "Compare the volumes or temperatures of two gas samples",
                                "Determine the relative volumes or temperatures of two gas samples"),

    # ---- level is right, verb was imprecise: Derive -> Determine (Apply) ------
    "CHEM_KIN1":         ("text", "Derive the unit of a reaction rate constant",
                                  "Determine the unit of a reaction rate constant"),
    "CHE_EQUILIBRIUM24": ("text", "Derive the expression for Kp",
                                  "Determine the expression for Kp"),

    # ---- level is right, verb was imprecise: -> Analyse (Analyze) -------------
    "CHEM_KIN14": ("text",
        "Determine the order of a reaction from experimental concentration-time, pressure-time, or titre-time data, by computing",
        "Analyze experimental concentration-time, pressure-time, or titre-time data to determine the order of a reaction, by computing"),
    "CHEM_PERIODIC17": ("text", "Compare the reaction behaviour of a hydrogen atom",
                                "Analyze the reaction behaviour of a hydrogen atom"),
    "CHE_ORGANIC114":  ("text", "Compare the boiling points of organic compounds",
                                "Analyze the boiling points of organic compounds"),
    "CHE_BONDING17":   ("text",
        "Determine which of several given full structural formulas for named compounds is chemically valid, by checking",
        "Examine several given full structural formulas for named compounds to determine which is chemically valid, by checking"),

    # ---- level is right, verb was imprecise: -> Classify/Distinguish (Understand)
    "CHEM_REDOX11":   ("text", "Identify which reagent functions as the oxidizing agent",
                               "Distinguish which reagent functions as the oxidizing agent"),
    "CHE_ACIDBASE51": ("text", "Identify whether a given mixture constitutes a buffer solution",
                               "Classify whether a given mixture constitutes a buffer solution"),
    "CHE_ACIDBASE56": ("text", "Identify the Bronsted-Lowry acid and the Bronsted-Lowry base",
                               "Classify the Bronsted-Lowry acid and the Bronsted-Lowry base"),
    "CHE_ACIDBASE60": ("text", "Identify which of several neutralization reactions",
                               "Classify which of several neutralization reactions"),
    "CHE_ORGANIC146": ("text", "Identify which of a set of given organic compounds can act as a monomer",
                               "Classify which of a set of given organic compounds can act as a monomer"),
    "CHE_ORGANIC150": ("text", "Recognize which carbonyl compounds can take part in an aldol condensation",
                               "Classify which carbonyl compounds can take part in an aldol condensation"),
    "CHE_ORGANIC154": ("text", "Identify which reagent distinguishes an alcohol from a phenol, and which distinguishes an aldehyde from a ketone, from the characteristic result each gives.",
                               "Distinguish an alcohol from a phenol, and an aldehyde from a ketone, by the reagent and the characteristic result each gives."),

    # ---- level is right, verb was imprecise: -> Explain/Interpret (Understand) -
    "CHEM_STEREO5":   ("text", "Recognize when the product of an addition to a symmetrical alkene",
                               "Explain when the product of an addition to a symmetrical alkene"),
    "CHE_ACIDBASE61": ("text", "Identify which hydrated metal-aqua complex ion is the most acidic",
                               "Explain which hydrated metal-aqua complex ion is the most acidic"),
    "CHE_ORGANIC144": ("text", "Identify which hydrogen atoms in a given molecule are the most acidic",
                               "Explain which hydrogen atoms in a given molecule are the most acidic"),
    "CHE_ORGANIC148": ("text", "Identify the role played by each reagent in a nitration mixture",
                               "Explain the role played by each reagent in a nitration mixture"),
    "CHE_ORGANIC52":  ("text", "Define the octane number of a motor fuel",
                               "Interpret the octane number of a motor fuel"),

    # ---- these five ALSO needed a level change above; reword so the verb agrees
    "CHEM_PERIODIC4_v":      ("text", "Identify the element matching a given periodic-property superlative",
                                      "Determine the element matching a given periodic-property superlative"),
    "CHE_ACIDBASE58_v":      ("text", "Identify the conjugate base of a given Bronsted acid",
                                      "Determine the conjugate base of a given Bronsted acid"),
    "CHE_EQUILIBRIUM16_v":   ("text", "Compare the molar solubilities of two different sparingly soluble salts",
                                      "Determine the relative molar solubilities of two different sparingly soluble salts"),
    "CHE_ORGANIC151_v":      ("text", "Identify which type of alcohol a Grignard reagent gives",
                                      "Predict which type of alcohol a Grignard reagent gives"),
    "CHE_STOICHIOMETRY34_v": ("text", "Identify the limiting reactant in a reaction",
                                      "Determine the limiting reactant in a reaction"),

    # ---- level is right, verb was imprecise: -> Write/Determine (Apply) -------
    "CHE_ORGANIC89": ("text", "Explain and write the use of acetylation",
                              "Write the use of acetylation"),
    "CHE_QUAL16":    ("text",
        "Interpret the observed result of a qualitative-analysis test (e.g., a white precipitate forming after adding bromine water and barium chloride to a sample and warming it) to identify which ion was present in the original solution.",
        "Determine which ion was present in the original solution from the observed result of a qualitative-analysis test (e.g., a white precipitate forming after adding bromine water and barium chloride to a sample and warming it)."),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    path = HERE / "tuples.json"
    tuples = json.loads(path.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    # A "_v" suffix means "same skill, second (wording) decision" — five skills
    # needed both a level correction and a reword so the verb agrees with it.
    def resolve(key: str) -> str:
        return key[:-2] if key.endswith("_v") else key

    missing = sorted({resolve(k) for k in DECISIONS} - set(by_id))
    if missing:
        sys.exit(f"error: skillIds not found in tuples.json: {missing}")

    bloom_changes, text_changes, problems, already = [], [], [], []

    for key, decision in sorted(DECISIONS.items()):
        sid = resolve(key)
        skill = by_id[sid]
        if decision[0] == "bloom":
            new_level = decision[1]
            if skill["bloom"] == new_level:
                already.append(f"{sid}: level already {new_level}")
                continue
            bloom_changes.append((sid, skill["bloom"], new_level))
            if args.apply:
                skill["bloom"] = new_level
        else:
            _, old, new = decision
            if new in skill["skillFull"] and old not in skill["skillFull"]:
                already.append(f"{sid}: wording already applied")
                continue
            count = skill["skillFull"].count(old)
            if count != 1:
                problems.append(f"{sid}: fragment occurs {count}x, expected exactly 1")
                continue
            text_changes.append((sid, old, new))
            if args.apply:
                skill["skillFull"] = skill["skillFull"].replace(old, new)

    print(f"level corrections : {len(bloom_changes)}")
    for sid, old, new in bloom_changes:
        print(f"    {sid:22} {old:>10} -> {new}")
    print(f"\nwording corrections: {len(text_changes)}")
    for sid, old, new in text_changes:
        print(f"    {sid:22} {old.split()[0]:>10} -> {new.split()[0]}")

    if already:
        print(f"\nalready applied (idempotent skip): {len(already)}")

    if problems:
        print("\nPROBLEMS (nothing written):")
        for p in problems:
            print("    " + p)
        sys.exit(1)

    if args.apply:
        path.write_text(
            json.dumps(tuples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\napplied {len(bloom_changes) + len(text_changes)} fixes to {path.name}")
    else:
        print("\n(dry run; nothing written)")


if __name__ == "__main__":
    main()
