"""Attach small disconnected fragments to their topic's spine.

This is the reviewed output of `_propose_fragment_links.py`. That script
proposed 83 edges mechanically; each was read, and **40 survived**. The rest
were rejected for reasons worth recording, because they are the reasons this
step cannot be automated:

  - *lateral links between siblings.* Zero-order kinetics does not require
    first-order kinetics; Tollens' reagent does not require Fehling's. They are
    peers under a common parent. Two proposals even came back as a mutual pair,
    which would have closed a cycle.
  - *backwards.* "Recall that the periodic table is arranged by atomic number"
    was proposed as requiring "recall the periodic trends in radius". The
    dependency runs the other way; several of these are applied here reversed.
  - *unrelated but same-topic.* Avogadro's law proposed as requiring Dalton's
    law of partial pressures; the definition of ppm as requiring the definition
    of normality. Same chapter, no dependency.

The 43 rejected fragments are left disconnected on purpose. A wrong
prerequisite edge propagates through the ancestor pull-up and silently corrupts
mastery estimates downstream, which is worse than a missing one. They are the
clearest remaining place where a chemist or a physicist adds value that no
heuristic can.

Idempotent. `--dry-run` reports and writes nothing; refuses to write on a cycle.
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

# (child, parent) - child requires parent
LINKS = [
    # --- Chemistry: acids, bases and buffers ---------------------------------
    ("CHE_ACIDBASE27", "CHE_ACIDBASE26"),   # H-H equation <- what a buffer is
    ("CHE_ACIDBASE53", "CHE_ACIDBASE43"),   # indicator colour <- definition of pH

    # --- atomic structure and electron configuration -------------------------
    ("CHE_ATOMIC52", "CHE_ATOMIC37"),       # valence patterns <- noble-gas pattern
    ("CHE_ATOMIC48", "CHE_ATOMIC10"),       # 2n^2 <- subshell capacities
    ("CHE_ATOMIC14", "CHE1_ELECTRON_CONFIG1"),  # Hund <- the three filling rules
    ("CHE_ATOMIC41", "CHE_ATOMIC6"),        # range of l <- what each quantum number means
    ("CHEM_SPEC6", "CHEM_SPEC3"),           # visible range <- regions of the EM spectrum

    # --- bonding -------------------------------------------------------------
    ("CHE_BONDING12", "CHE1_COVALENT_BOND0"),   # repulsion order <- VSEPR postulate
    ("CHE_BONDING24", "CHE1_COVALENT_BOND0"),   # Lewis structures <- electron pairs
    ("CHE_BONDING7", "CHE_BONDING22"),          # sigma/pi formation <- what a pi bond is
    ("CHE_BONDING45", "CHE1_IONIC_BOND0"),      # bond polarity <- ionic/covalent character
    ("CHE_BONDING30", "CHE_BONDING43"),         # can it H-bond <- intermolecular forces

    # --- thermochemistry -----------------------------------------------------
    ("CHE_THERMOCHEM12", "CHE_THERMOCHEM11"),
    ("CHE_THERMOCHEM15", "CHE_THERMOCHEM11"),
    ("CHE_THERMOCHEM8", "CHE_THERMOCHEM11"),

    # --- equilibrium ---------------------------------------------------------
    ("CHE_EQUILIBRIUM31", "CHE_EQUILIBRIUM30"),
    ("CHE_EQUILIBRIUM29", "CHE_EQUILIBRIUM30"),

    # --- kinetics. CHEM_KIN21 (what a reaction rate IS) is the real root of
    #     this chapter, so the Arrhenius equation is hung off it rather than the
    #     reverse, which is how the proposal came back.
    ("CHEM_KIN18", "CHEM_KIN21"),
    ("CHEM_KIN2", "CHEM_KIN21"),
    ("CHEM_KIN10", "CHEM_KIN21"),
    ("CHEM_KIN20", "CHEM_KIN21"),
    ("CHEM_KIN23", "CHEM_KIN21"),

    # --- gases ---------------------------------------------------------------
    ("CHE_GASLAWS38", "CHE_GASLAWS26"),     # Avogadro's law <- what an ideal gas is
    ("CHE_GASLAWS40", "CHE_GASLAWS26"),     # pressure units <- what an ideal gas is
    ("CHE_GASLAWS32", "CHE_GASLAWS26"),     # degrees of freedom <- ideal gas
    ("CHE_GASLAWS19", "CHE_GASLAWS26"),     # Graham's law <- ideal gas

    # --- periodic table. Proposal had this one backwards. --------------------
    ("CHE1_PERIODIC_TRENDS0", "CHEM_PERIODIC37"),  # trends <- how the table is ordered
    ("CHEM_PERIODIC27", "CHE1_PERIODIC_TRENDS0"),  # electron affinity <- radius trends
    ("CHEM_PERIODIC34", "CHE1_PERIODIC_TRENDS1"),  # oxide acidity <- metal/non-metal oxides

    # --- redox, nuclear, transition metals -----------------------------------
    ("CHEM_REDOX19", "CHE1_REDOX0"),
    ("CHEM_REDOX21", "CHE1_REDOX0"),
    ("CHEM_NUCLEAR16", "CHEM_NUCLEAR1"),
    ("CHEM_NUCLEAR8", "CHEM_NUCLEAR1"),
    ("CHEM_DBLOCK2", "CHE1_TRANSITION0"),
    ("CHE_COORD11", "CHE_COORD3"),

    # --- solutions, analysis, lab -------------------------------------------
    ("CHEM_SOLUTION17", "CHEM_SOLUTION14"),
    ("CHEM_SOLUTION3", "CHEM_SOLUTION7"),
    ("CHEM_ANALYTICAL10", "CHEM_ANALYTICAL4"),  # reversed: titration <- standard solution
    ("CHEM_LAB8", "CHEM_LAB0"),

    # --- biomolecules. Anchored on the biopolymer classification, not on the
    #     amino-acid skill the proposal kept picking.
    ("CHE_BIOMOLECULE13", "CHE_BIOMOLECULE11"),
    ("CHE_BIOMOLECULE12", "CHE_BIOMOLECULE11"),
    ("CHE_BIOMOLECULE16", "CHE_BIOMOLECULE11"),
    ("CHE_BIOMOLECULE7", "CHE_BIOMOLECULE11"),

    # --- Mathematics ---------------------------------------------------------
    ("MAT_TRIG30", "MAT_TRIG29"),               # cosine rule after sine rule (NCTB order)
    ("MAT2_TRIG_EQUATION5", "MAT2_TRIG_EQUATION0"),
    ("MAT1_LIMIT12", "MAT1_LIMIT5"),
    ("MAT2_POLY_ROOTS4", "MAT2_POLYNOMIAL9"),   # remaining roots <- factor theorem

    # --- Physics -------------------------------------------------------------
    ("PHY2_HEAT_TEMPERATURE3", "PHY2_HEAT_TEMPERATURE0"),  # reversed from proposal
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    prereqs = json.loads(PREREQS.read_text(encoding="utf-8"))
    D = {t["skillId"]: t for t in tuples}

    for a, b in LINKS:
        for x in (a, b):
            if x not in D:
                sys.exit("ABORT: unknown skill %s" % x)
        if a == b:
            sys.exit("ABORT: self edge %s" % a)

    parents = collections.defaultdict(set)
    for c, v in prereqs.items():
        for p in v:
            parents[c].add(p["id"])
    added = [(c, p) for c, p in LINKS if p not in parents[c]]
    for c, p in LINKS:
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

    print("reviewed proposals : 83")
    print("accepted           : %d" % len(LINKS))
    print("new (not already present): %d" % len(added))
    print("no cycle           : OK")

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    for f in (TUPLES, PREREQS):
        shutil.copy2(f, BACKUP / (f.stem + ".pre_fraglinks.json"))

    full_of = {t["skillId"]: t["skillFull"] for t in tuples}
    out = {}
    for c in sorted(parents):
        if c not in full_of:
            continue
        plist = [{"id": p, "full": full_of[p], "depth": 0}
                 for p in sorted(parents[c]) if p in full_of]
        if plist:
            out[c] = plist
    PREREQS.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nwrote prereqs.json (%d edges)" % sum(len(v) for v in out.values()))


if __name__ == "__main__":
    main()
