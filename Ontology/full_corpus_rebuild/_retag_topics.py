"""Re-file skills onto the correct HSC/NCTB syllabus topic.

WHY THIS EXISTS
---------------
`ontology_config.json::topic_aliases` is a **code-to-code** map: one old topic
code collapses onto exactly one syllabus code. But the syllabus splits most of
those old buckets into several topics. So `CHE_ORGANIC` -> `CHE2_ORG_HYDROCARBON`
put all 154 organic skills into "Hydrocarbons" while eight sibling topics
(alcohols, carbonyls, amines, polymers, ...) reported zero skills.

An alias cannot fix that, because the split is **per skill**, not per code. This
script carries the per-skill decision and rewrites `topicKey` / `topicLabel` in
`tuples.json` directly, so the rebuild becomes self-describing and no longer
depends on aliases for the chapters it touches.

The `RETAG` table below is the deliverable - one editorial judgement per skill.
Read it before trusting the result.

SAFETY
------
- refuses to run if any target topic is not in the syllabus vocabulary;
- refuses to run if a skillId in the table does not exist;
- backs up tuples.json to _prefix_backup/ before writing;
- idempotent: re-running changes nothing;
- `--dry-run` reports the plan and writes nothing.

Usage:
    python _retag_topics.py --dry-run
    python _retag_topics.py
"""
import argparse
import json
import pathlib
import shutil
import sys
import collections

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
TUPLES = HERE / "tuples.json"
CONFIG = REPO / "Backend" / "tree_data" / "ontology_config.json"
BACKUP = HERE / "_prefix_backup"


# ---------------------------------------------------------------------------
# MATHEMATICS
# ---------------------------------------------------------------------------
# HM 1st Paper Ch1 - Matrices and Determinants.
# The old MAT_MATRIX bucket held all three: matrix arithmetic, determinant
# evaluation and its properties, and inverses. Splitting on what the task is
# *about*, not on what notation it happens to use: MAT_MATRIX30 (solving a 3x3
# linear system by determinants) is Cramer's rule, so it is determinant work,
# while MAT_MATRIX4 (parameter making a matrix singular) is asked in order to
# decide whether an inverse exists.
MATH = {
    "MAT1_MATRIX_ALGEBRA": """
        MAT_MATRIX5 MAT_MATRIX6 MAT_MATRIX7 MAT_MATRIX8 MAT_MATRIX9
        MAT_MATRIX10 MAT_MATRIX11 MAT_MATRIX12 MAT_MATRIX29 MAT_MATRIX31
    """,
    "MAT1_DETERMINANT": """
        MAT_MATRIX2 MAT_MATRIX13 MAT_MATRIX14 MAT_MATRIX15 MAT_MATRIX16
        MAT_MATRIX17 MAT_MATRIX18 MAT_MATRIX19 MAT_MATRIX20 MAT_MATRIX21
        MAT_MATRIX22 MAT_MATRIX23 MAT_MATRIX24 MAT_MATRIX30
    """,
    "MAT1_INVERSE": """
        MAT_MATRIX4 MAT_MATRIX25 MAT_MATRIX26 MAT_MATRIX27 MAT_MATRIX28
    """,

    # Ch2 - Vector. MATH_MECH was a single code covering vectors, statics and
    # dynamics; the statics/dynamics half already moved to MAT2_* in earlier
    # batches, leaving these 19. Split: components and basic algebra; the two
    # products and everything computed straight from them; and the geometric
    # applications (areas, coplanarity, polygon resultants).
    "MAT1_VECTOR_ALGEBRA": """
        MATH_MECH10 MATH_MECH11 MATH_MECH15 MATH_MECH24 MATH_MECH26 MATH_MECH28
    """,
    "MAT1_VECTOR_PRODUCT": """
        MATH_MECH12 MATH_MECH13 MATH_MECH14 MATH_MECH16 MATH_MECH17
        MATH_MECH20 MATH_MECH22 MATH_MECH23 MATH_MECH25
    """,
    "MAT1_VECTOR_GEOMETRY": """
        MATH_MECH18 MATH_MECH19 MATH_MECH21 MATH_MECH27
    """,

    # Ch3 - Straight Line. Four-way split following the topic labels:
    # "Coordinates, Distance and Slope" takes the pre-equation groundwork
    # (section formula, midpoints, rotation of axes, figures from vertices);
    # "Equations of a Straight Line" takes anything whose answer IS an equation;
    # "Angles, Distances and Pairs of Lines" takes every two-line or
    # point-to-line relation (parallel/perpendicular tests, angle, perpendicular
    # distance, foot of perpendicular, reflection, bisectors, concurrency);
    # "Polar Coordinates" takes the polar block.
    "MAT1_LINE_BASICS": """
        MAT_COORD_LINE9 MAT_COORD_LINE10 MAT_COORD_LINE30 MAT_COORD_LINE31
        MAT_COORD_LINE32 MAT_COORD_LINE37 MAT_COORD_LINE38 MAT_COORD_LINE39
        MAT_COORD_LINE46
    """,
    "MAT1_LINE_EQUATION": """
        MAT_COORD_LINE16 MAT_COORD_LINE17 MAT_COORD_LINE20 MAT_COORD_LINE24
        MAT_COORD_LINE25 MAT_COORD_LINE26 MAT_COORD_LINE27 MAT_COORD_LINE28
        MAT_COORD_LINE29 MAT_COORD_LINE40 MAT_COORD_LINE41 MAT_COORD_LINE43
        MAT_COORD_LINE45 MAT_COORD_LINE47 MAT_COORD_LINE48
    """,
    "MAT1_LINE_PAIR": """
        MAT_COORD_LINE11 MAT_COORD_LINE12 MAT_COORD_LINE13 MAT_COORD_LINE14
        MAT_COORD_LINE15 MAT_COORD_LINE18 MAT_COORD_LINE19 MAT_COORD_LINE21
        MAT_COORD_LINE22 MAT_COORD_LINE23 MAT_COORD_LINE44
    """,
    "MAT1_POLAR": """
        MAT_COORD_LINE33 MAT_COORD_LINE34 MAT_COORD_LINE35 MAT_COORD_LINE36
        MAT_COORD_LINE42
    """,

    # Ch4 - Circle. "Equation of a Circle" keeps everything whose answer is the
    # circle itself (including the touches-an-axis constructions, which are
    # equation-finding problems that merely use a tangency condition) plus the
    # circle's own mensuration. "Tangents and Normals" takes the tangent/chord
    # family. "Two Circles" takes the three genuinely two-circle skills.
    "MAT1_CIRCLE_EQUATION": """
        MAT_COORD_CONIC6 MAT_COORD_CONIC7 MAT_COORD_CONIC8 MAT_COORD_CONIC9
        MAT_COORD_CONIC10 MAT_COORD_CONIC11 MAT_COORD_CONIC12 MAT_COORD_CONIC13
        MAT_COORD_CONIC26 MAT_COORD_CONIC27 MAT_COORD_CONIC28 MAT_COORD_CONIC29
        MAT_COORD_CONIC30 MAT_COORD_CONIC31 MAT_COORD_CONIC32 MAT_COORD_CONIC33
    """,
    "MAT1_CIRCLE_TANGENT": """
        MAT_COORD_CONIC14 MAT_COORD_CONIC15 MAT_COORD_CONIC16 MAT_COORD_CONIC17
        MAT_COORD_CONIC18 MAT_COORD_CONIC19 MAT_COORD_CONIC20 MAT_COORD_CONIC21
        MAT_COORD_CONIC22
    """,
    "MAT1_CIRCLE_PAIR": """
        MAT_COORD_CONIC23 MAT_COORD_CONIC24 MAT_COORD_CONIC25
    """,

    # Ch5 - Permutation and Combination. Order matters -> Permutations;
    # order does not -> Combinations (including the nCr identities); and the
    # word-problem applications where the student must first model the
    # situation -> Applications of Counting.
    "MAT1_PERMUTATION": """
        MAT_PERMCOMB0 MAT_PERMCOMB1 MAT_PERMCOMB4 MAT_PERMCOMB5 MAT_PERMCOMB6
        MAT_PERMCOMB8 MAT_PERMCOMB13
    """,
    "MAT1_COMBINATION": """
        MAT_PERMCOMB2 MAT_PERMCOMB3 MAT_PERMCOMB7 MAT_PERMCOMB14
        MAT_PERMCOMB15 MAT_PERMCOMB16 MAT_PERMCOMB20
    """,
    "MAT1_COUNTING_APP": """
        MAT_PERMCOMB9 MAT_PERMCOMB10 MAT_PERMCOMB11 MAT_PERMCOMB12
        MAT_PERMCOMB17 MAT_PERMCOMB18 MAT_PERMCOMB19
    """,

    # Ch6 + Ch7 - Trigonometry. The old MAT_TRIG code covered both chapters at
    # once, which is why Ch6 reported as a completely empty section. Four of
    # these skills are not Ch6/Ch7 material at all and move to their real
    # 2nd-Paper chapters: three are trigonometric equations and one evaluates an
    # expression whose angle is given by an inverse function.
    "MAT1_TRIG_RATIOS": """
        MAT_TRIG4 MAT_TRIG5 MAT_TRIG8 MAT_TRIG9 MAT_TRIG36 MAT_TRIG37 MAT_TRIG38
    """,
    "MAT1_TRIG_ANGLES": """
        MAT_TRIG10 MAT_TRIG11 MAT_TRIG12
    """,
    "MAT1_COMPOUND_ANGLE": """
        MAT_TRIG13 MAT_TRIG14 MAT_TRIG15 MAT_TRIG24 MAT_TRIG28
    """,
    "MAT1_MULTIPLE_ANGLE": """
        MAT_TRIG7 MAT_TRIG16 MAT_TRIG17 MAT_TRIG25 MAT_TRIG27
    """,
    "MAT1_SUM_PRODUCT": """
        MAT_TRIG18 MAT_TRIG19 MAT_TRIG20 MAT_TRIG26
    """,
    "MAT1_TRIANGLE_PROPS": """
        MAT_TRIG6 MAT_TRIG29 MAT_TRIG30 MAT_TRIG31 MAT_TRIG32 MAT_TRIG33
        MAT_TRIG34 MAT_TRIG35
    """,
    "MAT2_TRIG_EQUATION": """
        MAT_TRIG21 MAT_TRIG22 MAT_TRIG23
    """,
    "MAT2_INVERSE_TRIG": """
        MAT_TRIG39
    """,

    # Ch8 - Functions. Domain/range/definition stay in "Functions, Domain and
    # Range"; composition and inverse form their own topic; the two graph-reading
    # skills form theirs. MAT_FUNCTION17 is a quadratic inequality wearing a
    # function costume and belongs to 2nd-Paper Inequalities.
    "MAT1_FUNCTION_BASICS": """
        MAT_FUNCTION0 MAT_FUNCTION1 MAT_FUNCTION2 MAT_FUNCTION8 MAT_FUNCTION9
        MAT_FUNCTION10 MAT_FUNCTION11 MAT_FUNCTION13 MAT_FUNCTION15
        MAT_FUNCTION18
    """,
    "MAT1_FUNCTION_COMPOSE": """
        MAT_FUNCTION3 MAT_FUNCTION4 MAT_FUNCTION5 MAT_FUNCTION6 MAT_FUNCTION7
        MAT_FUNCTION12
    """,
    "MAT1_FUNCTION_GRAPH": """
        MAT_FUNCTION14 MAT_FUNCTION16
    """,
    "MAT2_INEQUALITY": """
        MAT_FUNCTION17
    """,
}


# ---------------------------------------------------------------------------
# CHEMISTRY - Organic (Chem 2nd Paper Ch2)
# ---------------------------------------------------------------------------
# The worst case in the whole ontology: 154 skills under CHE2_ORG_HYDROCARBON
# while eight sibling topics reported zero. Filed by the compound class the
# skill is *about*, which for a named reaction means the class of its
# substrate, not of its product - so free-radical chlorination of methane is
# an alkane reaction (HYDROCARBON) even though it makes a halide, and nitrile
# hydrolysis is filed by its carboxylic-acid product only because the nitrile
# itself has no topic.
#
# Judgement calls worth knowing about:
#   - ethers have no topic of their own in the syllabus, so they sit with
#     ALCOHOL, which is where the NCTB book teaches them;
#   - amides, anhydrides and esters sit with ACID as acid derivatives;
#   - ORG_BASICS collects the mechanism-and-structure skills that are not tied
#     to one class: isomerism, homologous series, electrophile/nucleophile,
#     carbocation stability, multi-step deduction, boiling-point trends.
CHEM_ORGANIC = {
    "CHE2_ORG_BASICS": """
        CHE_ORGANIC5 CHE_ORGANIC8 CHE_ORGANIC9 CHE_ORGANIC14 CHE_ORGANIC20
        CHE_ORGANIC21 CHE_ORGANIC72 CHE_ORGANIC74 CHE_ORGANIC97 CHE_ORGANIC98
        CHE_ORGANIC100 CHE_ORGANIC101 CHE_ORGANIC107 CHE_ORGANIC111
        CHE_ORGANIC114 CHE_ORGANIC116 CHE_ORGANIC143 CHE_ORGANIC154
        CHE_ORGANIC155 CHE_ORGANIC156 CHE_ORGANIC157
    """,
    "CHE2_ORG_HYDROCARBON": """
        CHE_ORGANIC6 CHE_ORGANIC38 CHE_ORGANIC39 CHE_ORGANIC40 CHE_ORGANIC52
        CHE_ORGANIC73 CHE_ORGANIC75 CHE_ORGANIC78 CHE_ORGANIC84 CHE_ORGANIC85
        CHE_ORGANIC86 CHE_ORGANIC87 CHE_ORGANIC99 CHE_ORGANIC109 CHE_ORGANIC110
        CHE_ORGANIC121 CHE_ORGANIC123 CHE_ORGANIC132 CHE_ORGANIC133
        CHE_ORGANIC137 CHE_ORGANIC141 CHE_ORGANIC142
    """,
    "CHE2_ORG_AROMATIC": """
        CHE_ORGANIC7 CHE_ORGANIC12 CHE_ORGANIC13 CHE_ORGANIC41 CHE_ORGANIC71
        CHE_ORGANIC76 CHE_ORGANIC77 CHE_ORGANIC79 CHE_ORGANIC95 CHE_ORGANIC106
        CHE_ORGANIC112 CHE_ORGANIC124 CHE_ORGANIC127 CHE_ORGANIC136
        CHE_ORGANIC145 CHE_ORGANIC147 CHE_ORGANIC148
    """,
    "CHE2_ORG_HALIDE": """
        CHE_ORGANIC46 CHE_ORGANIC68 CHE_ORGANIC69 CHE_ORGANIC80 CHE_ORGANIC81
        CHE_ORGANIC82 CHE_ORGANIC94 CHE_ORGANIC96 CHE_ORGANIC108
        CHE_ORGANIC134 CHE_ORGANIC135 CHE_ORGANIC149
    """,
    "CHE2_ORG_ALCOHOL": """
        CHE_ORGANIC23 CHE_ORGANIC24 CHE_ORGANIC33 CHE_ORGANIC34 CHE_ORGANIC35
        CHE_ORGANIC36 CHE_ORGANIC37 CHE_ORGANIC58 CHE_ORGANIC59 CHE_ORGANIC60
        CHE_ORGANIC62 CHE_ORGANIC63 CHE_ORGANIC64 CHE_ORGANIC70 CHE_ORGANIC122
        CHE_ORGANIC129 CHE_ORGANIC130 CHE_ORGANIC138 CHE_ORGANIC140
        CHE_ORGANIC152 CHE_ORGANIC153
    """,
    "CHE2_ORG_CARBONYL": """
        CHE_ORGANIC15 CHE_ORGANIC16 CHE_ORGANIC17 CHE_ORGANIC18 CHE_ORGANIC19
        CHE_ORGANIC22 CHE_ORGANIC42 CHE_ORGANIC43 CHE_ORGANIC44 CHE_ORGANIC45
        CHE_ORGANIC61 CHE_ORGANIC83 CHE_ORGANIC92 CHE_ORGANIC113
        CHE_ORGANIC120 CHE_ORGANIC144 CHE_ORGANIC150 CHE_ORGANIC151
    """,
    "CHE2_ORG_ACID": """
        CHE_ORGANIC10 CHE_ORGANIC11 CHE_ORGANIC25 CHE_ORGANIC26 CHE_ORGANIC47
        CHE_ORGANIC48 CHE_ORGANIC49 CHE_ORGANIC50 CHE_ORGANIC51 CHE_ORGANIC65
        CHE_ORGANIC66 CHE_ORGANIC67 CHE_ORGANIC102 CHE_ORGANIC103
        CHE_ORGANIC115 CHE_ORGANIC117 CHE_ORGANIC118 CHE_ORGANIC119
        CHE_ORGANIC139
    """,
    "CHE2_ORG_AMINE": """
        CHE_ORGANIC4 CHE_ORGANIC27 CHE_ORGANIC28 CHE_ORGANIC29 CHE_ORGANIC30
        CHE_ORGANIC31 CHE_ORGANIC32 CHE_ORGANIC88 CHE_ORGANIC89 CHE_ORGANIC90
        CHE_ORGANIC91 CHE_ORGANIC93 CHE_ORGANIC104 CHE_ORGANIC105
        CHE_ORGANIC125 CHE_ORGANIC126 CHE_ORGANIC128
    """,
    "CHE2_ORG_POLYMER": """
        CHE_ORGANIC53 CHE_ORGANIC54 CHE_ORGANIC55 CHE_ORGANIC56 CHE_ORGANIC57
        CHE_ORGANIC131 CHE_ORGANIC146
    """,
}


# ---------------------------------------------------------------------------
# CHEMISTRY - everything except organic
# ---------------------------------------------------------------------------
CHEM = {
    # --- Chem 1st Paper Ch1, Safe Use of the Laboratory ---------------------
    "CHE1_LAB_APPARATUS": "CHEM_LAB0 CHEM_LAB2 CHEM_LAB8 CHEM_LAB9 CHEM_LAB14",
    "CHE1_LAB_SAFETY": "CHEM_LAB3 CHEM_LAB4 CHEM_LAB5 CHEM_LAB6",
    "CHE1_LAB_SEPARATION": "CHEM_LAB12 CHEM_LAB13",
    "CHE1_LAB_REAGENTS": "CHEM_LAB1 CHEM_LAB7 CHEM_LAB10 CHEM_LAB11 CHEM_LAB15",

    # --- Ch2, Qualitative Chemistry ----------------------------------------
    # CHEM_DESCRIPTIVE4/5 move in from Ch5: both are flame-test skills that
    # were sitting in descriptive inorganic chemistry.
    "CHE1_FLAME_TEST": "CHE_QUAL6 CHE_QUAL22 CHEM_DESCRIPTIVE4 CHEM_DESCRIPTIVE5",
    "CHE1_CATION_ANALYSIS": """
        CHE_QUAL2 CHE_QUAL3 CHE_QUAL4 CHE_QUAL7 CHE_QUAL10 CHE_QUAL19
        CHE_QUAL20 CHE_QUAL23
    """,
    "CHE1_ANION_ANALYSIS": "CHE_QUAL9 CHE_QUAL14 CHE_QUAL15",
    "CHE1_CONFIRMATORY": """
        CHE_QUAL5 CHE_QUAL8 CHE_QUAL11 CHE_QUAL13 CHE_QUAL16 CHE_QUAL21
    """,
    "CHE1_SOLUBILITY_RULES": "CHE_QUAL12 CHE_QUAL17 CHE_QUAL18",

    # --- Ch3, Periodic Properties and Chemical Bonding ---------------------
    # CHE1_ATOMIC_STRUCTURE held 62 skills covering three distinct things.
    # Nucleus / isotopes / quantum numbers / orbital shapes stay; the
    # configuration-writing family becomes ELECTRON_CONFIG; and the hydrogen
    # spectrum family joins the ATOMIC_SPECTRA topic that already existed but
    # had only 7 skills. Two ionisation-energy skills move to PERIODIC_TRENDS.
    "CHE1_ATOMIC_STRUCTURE": """
        CHEM_ATOMIC5 CHE_ATOMIC6 CHE_ATOMIC7 CHE_ATOMIC8 CHE_ATOMIC17
        CHE_ATOMIC18 CHE_ATOMIC19 CHE_ATOMIC21 CHE_ATOMIC29 CHE_ATOMIC30
        CHE_ATOMIC31 CHE_ATOMIC32 CHE_ATOMIC33 CHE_ATOMIC34 CHE_ATOMIC35
        CHE_ATOMIC38 CHE_ATOMIC39 CHE_ATOMIC40 CHE_ATOMIC41 CHE_ATOMIC42
        CHE_ATOMIC44 CHE_ATOMIC45 CHE_ATOMIC56 CHE_ATOMIC59 CHE_ATOMIC64
    """,
    "CHE1_ELECTRON_CONFIG": """
        CHEM_AT1 CHE_ATOMIC2 CHE_ATOMIC9 CHE_ATOMIC10 CHE_ATOMIC11
        CHE_ATOMIC12 CHE_ATOMIC13 CHE_ATOMIC14 CHE_ATOMIC15 CHE_ATOMIC16
        CHE_ATOMIC20 CHE_ATOMIC36 CHE_ATOMIC37 CHE_ATOMIC46 CHE_ATOMIC47
        CHE_ATOMIC48 CHE_ATOMIC52 CHE_ATOMIC55 CHE_ATOMIC57 CHE_ATOMIC58
        CHE_ATOMIC60 CHE_ATOMIC61 CHE_ATOMIC62 CHE_ATOMIC63
    """,
    "CHE1_ATOMIC_SPECTRA": """
        CHE_ATOMIC22 CHE_ATOMIC23 CHE_ATOMIC24 CHE_ATOMIC25 CHE_ATOMIC26
        CHE_ATOMIC27 CHE_ATOMIC28 CHE_ATOMIC43 CHE_ATOMIC49 CHE_ATOMIC50
        CHE_ATOMIC51
    """,
    "CHE1_PERIODIC_TRENDS": "CHE_ATOMIC53 CHE_ATOMIC54",

    # CHE1_COVALENT_BOND held 54. Ionic/metallic lattice behaviour and the
    # polarising-power family become IONIC_BOND; hydrogen bonding and the
    # boiling-point comparisons become INTERMOLECULAR; VSEPR, hybridisation,
    # orbital overlap and Lewis structures stay covalent.
    "CHE1_IONIC_BOND": """
        CHE_BONDING6 CHE_BONDING21 CHE_BONDING32 CHE_BONDING34 CHE_BONDING38
        CHE_BONDING44 CHE_BONDING45 CHE_BONDING48
    """,
    "CHE1_INTERMOLECULAR": """
        CHE_BONDING25 CHE_BONDING30 CHE_BONDING43 CHE_BONDING49 CHE_BONDING56
    """,
    "CHE1_COVALENT_BOND": """
        CHE_BONDING3 CHE_BONDING4 CHE_BONDING5 CHE_BONDING7 CHE_BONDING8
        CHE_BONDING9 CHE_BONDING10 CHE_BONDING11 CHE_BONDING12 CHE_BONDING13
        CHE_BONDING14 CHE_BONDING15 CHE_BONDING16 CHE_BONDING17 CHE_BONDING18
        CHE_BONDING19 CHE_BONDING20 CHE_BONDING22 CHE_BONDING23 CHE_BONDING24
        CHE_BONDING26 CHE_BONDING27 CHE_BONDING28 CHE_BONDING29 CHE_BONDING31
        CHE_BONDING33 CHE_BONDING35 CHE_BONDING36 CHE_BONDING37 CHE_BONDING39
        CHE_BONDING40 CHE_BONDING41 CHE_BONDING42 CHE_BONDING46 CHE_BONDING47
        CHE_BONDING50 CHE_BONDING51 CHE_BONDING52 CHE_BONDING53 CHE_BONDING54
        CHE_BONDING55
    """,

    # --- Ch4, Chemical Changes ---------------------------------------------
    # Buffers and salt hydrolysis pulled out of the 62-skill acid-base bucket.
    "CHE1_BUFFER": """
        CHE_ACIDBASE10 CHE_ACIDBASE14 CHE_ACIDBASE20 CHE_ACIDBASE26
        CHE_ACIDBASE27 CHE_ACIDBASE28 CHE_ACIDBASE29 CHE_ACIDBASE30
        CHE_ACIDBASE31 CHE_ACIDBASE41 CHE_ACIDBASE42 CHE_ACIDBASE44
        CHE_ACIDBASE51 CHE_ACIDBASE52 CHE_ACIDBASE55 CHE_ACIDBASE61
    """,

    # --- Chem 2nd Paper Ch1, Environmental Chemistry ------------------------
    # Kinetic theory and real-gas behaviour pulled out of the gas-law bucket:
    # molecular speeds, van der Waals, compressibility, degrees of freedom,
    # Joule-Thomson, and the diffusion/effusion family that follows from them.
    "CHE2_KINETIC_THEORY": """
        CHEM_GAS3 CHEM_GAS4 CHEM_GASLAW1 CHEM_GASLAW4 CHEM_GASLAW5
        CHE_GASLAWS7 CHE_GASLAWS8 CHE_GASLAWS9 CHE_GASLAWS10 CHE_GASLAWS19
        CHE_GASLAWS20 CHE_GASLAWS22 CHE_GASLAWS23 CHE_GASLAWS24 CHE_GASLAWS25
        CHE_GASLAWS26 CHE_GASLAWS31 CHE_GASLAWS32 CHE_GASLAWS33 CHE_GASLAWS34
        CHE_GASLAWS36 CHE_GASLAWS37 CHE_GASLAWS39
    """,
    "CHE2_ACID_RAIN": """
        CHEM_ENV3 CHEM_ENV4 CHEM_ENV11 CHEM_ENV15 CHEM_ENV16 CHEM_ENV20
        CHEM_ENV21
    """,
    "CHE2_WATER_SOIL": """
        CHEM_ENV5 CHEM_ENV10 CHEM_ENV12 CHEM_ENV14 CHEM_ENV18 CHEM_ENV25
        CHEM_ENV26 CHEM_ENV27 CHEM_ENV28
    """,
    "CHE2_GREEN_CHEM": "CHEM_ENV6 CHEM_ENV7 CHEM_ENV8 CHEM_ENV9",

    # --- Ch3, Quantitative Chemistry ---------------------------------------
    "CHE2_FORMULA": """
        CHE_STOICHIOMETRY5 CHE_STOICHIOMETRY6 CHE_STOICHIOMETRY7
        CHE_STOICHIOMETRY25 CHE_STOICHIOMETRY26 CHE_STOICHIOMETRY27
        CHE_STOICHIOMETRY28 CHE_STOICHIOMETRY30 CHE_STOICHIOMETRY33
        CHEM_ANALYTICAL14
    """,
    "CHE2_GRAVIMETRIC": """
        CHEM_ANALYTICAL15 CHE_STOICHIOMETRY23 CHE_STOICHIOMETRY24
    """,
    "CHE2_TITRATION": """
        CHEM_ANALYTICAL2 CHEM_ANALYTICAL3 CHEM_ANALYTICAL4 CHEM_ANALYTICAL5
        CHEM_ANALYTICAL6 CHEM_ANALYTICAL7 CHEM_ANALYTICAL8 CHEM_ANALYTICAL9
        CHEM_ANALYTICAL10 CHEM_ANALYTICAL11 CHEM_ANALYTICAL12
        CHEM_ANALYTICAL13 CHEM_ANALYTICAL16 CHEM_ANALYTICAL17
    """,
    "CHE2_FORMULA_FROM_TITRATION": "",  # placeholder removed below

    # --- Ch4, Electrochemistry ---------------------------------------------
    "CHE2_ELECTROLYSIS": """
        CHE_ELECTROCHEM2 CHE_ELECTROCHEM6 CHE_ELECTROCHEM7
    """,
    "CHE2_GALVANIC": """
        CHEM_ELECTROCHEM1 CHE_ELECTROCHEM1 CHE_ELECTROCHEM3 CHE_ELECTROCHEM4
        CHE_ELECTROCHEM5 CHE_ELECTROCHEM8
    """,
    "CHE2_BATTERY": "CHE_ELECTROCHEM9 CHE_ELECTROCHEM10",

    # --- Ch5, Economic Chemistry (and Chem 1st Ch5, Applied Chemistry) ------
    # che1_ch05 had no content whatever. Three glass/consumer-material skills
    # and two applied-process skills move there from descriptive chemistry,
    # which is where the syllabus actually teaches them.
    "CHE2_DESCRIPTIVE": """
        CHEM_DESCRIPTIVE0 CHEM_DESCRIPTIVE1 CHEM_DESCRIPTIVE8
        CHEM_DESCRIPTIVE10 CHEM_DESCRIPTIVE11 CHEM_DESCRIPTIVE12
        CHEM_DESCRIPTIVE15 CHEM_DESCRIPTIVE17 CHEM_DESCRIPTIVE20
        CHEM_DESCRIPTIVE21
    """,
    "CHE2_INDUSTRIAL": """
        CHEM_DESCRIPTIVE6 CHEM_DESCRIPTIVE9 CHEM_DESCRIPTIVE22
        CHEM_DESCRIPTIVE23
    """,
    "CHE2_METALLURGY": "CHEM_DESCRIPTIVE3",
    "CHE2_ALLOY": "CHEM_DESCRIPTIVE2 CHEM_DESCRIPTIVE13",
    "CHE1_APPLIED_MATERIALS": """
        CHEM_DESCRIPTIVE14 CHEM_DESCRIPTIVE16 CHEM_DESCRIPTIVE18
    """,
    "CHE1_APPLIED_PROCESS": "CHEM_DESCRIPTIVE7 CHEM_DESCRIPTIVE19",
}
del CHEM["CHE2_FORMULA_FROM_TITRATION"]


# ---------------------------------------------------------------------------
# PHYSICS
# ---------------------------------------------------------------------------
# Physics was extracted straight onto syllabus codes, so it needs almost
# nothing. The one move: inclined-plane-with-friction is the canonical friction
# problem of HSC Physics 1st Paper Ch4 and was the only thing standing between
# PHY1_FRICTION and being empty.
#
# PHY1_ERRORS and PHY1_SOLID_BONDING are left empty deliberately - a corpus-wide
# search for error / significant figure / least count / crystal / lattice
# returns nothing, so these are real gaps in the source books, not misfilings.
PHYSICS = {
    "PHY1_FRICTION": "PHY1_NEWTON_LAWS6",
}


RETAG_GROUPS = [
    ("Mathematics", MATH),
    ("Chemistry - organic", CHEM_ORGANIC),
    ("Chemistry - other", CHEM),
    ("Physics", PHYSICS),
]


# ---------------------------------------------------------------------------
def build_table():
    table = {}
    clashes = []
    for _subject, group in RETAG_GROUPS:
        for topic, blob in group.items():
            for sid in blob.split():
                if sid in table and table[sid] != topic:
                    clashes.append((sid, table[sid], topic))
                table[sid] = topic
    if clashes:
        sys.exit("ABORT: skill assigned to two topics: %r" % (clashes,))
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    table = build_table()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    labels = cfg.get("topic_labels", {})
    tuples = json.loads(TUPLES.read_text(encoding="utf-8"))
    by_id = {t["skillId"]: t for t in tuples}

    unknown_topic = sorted({v for v in table.values() if v not in labels})
    if unknown_topic:
        sys.exit("ABORT: target topics not in syllabus vocabulary: %s" % unknown_topic)
    missing = sorted(s for s in table if s not in by_id)
    if missing:
        sys.exit("ABORT: unknown skillIds in RETAG table: %s" % missing)

    # Skills the table does not name keep the topic they already resolve to,
    # but that topic is written out explicitly. After this run every skill in
    # tuples.json carries a syllabus code directly and `topic_aliases` becomes
    # a no-op for the rebuild - the editorial decision lives in RETAG, in one
    # place, instead of being split between a code map and the raw data.
    aliases = cfg.get("topic_aliases", {})
    for t in tuples:
        sid = t["skillId"]
        if sid not in table:
            canon = aliases.get(t["topicKey"], t["topicKey"])
            if canon in labels:
                table[sid] = canon

    moves = []
    for sid, topic in sorted(table.items()):
        t = by_id[sid]
        if t["topicKey"] != topic:
            moves.append((sid, t["topicKey"], topic))

    print("retag table   : %d skills" % len(table))
    print("already correct: %d" % (len(table) - len(moves)))
    print("to move        : %d" % len(moves))
    froms = collections.Counter(f for _s, f, _t in moves)
    tos = collections.Counter(t for _s, _f, t in moves)
    print("\n  out of:")
    for k, n in froms.most_common():
        print("    %-24s %d" % (k, n))
    print("  into:")
    for k, n in sorted(tos.items()):
        print("    %-24s %d" % (k, n))

    if args.dry_run:
        print("\n(dry run; nothing written)")
        return

    BACKUP.mkdir(exist_ok=True)
    shutil.copy2(TUPLES, BACKUP / "tuples.pre_retag.json")

    for sid, topic in table.items():
        t = by_id[sid]
        t["topicKey"] = topic
        lab = labels[topic]
        t["topicLabel"] = lab if isinstance(lab, str) else lab.get("en", topic)

    TUPLES.write_text(
        json.dumps(tuples, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("\nwrote %s (backup in _prefix_backup/tuples.pre_retag.json)" % TUPLES.name)


if __name__ == "__main__":
    main()
