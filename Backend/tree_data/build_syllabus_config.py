"""
build_syllabus_config.py
------------------------
Rebuild `ontology_config.json` around the actual HSC/NCTB syllabus instead of the
topic vocabulary an LLM happened to invent in two ad-hoc chat runs in 2024.

Why this exists
---------------
The original 66-topic list was never derived from a syllabus. It came from the two
sessions recorded in `Ontology/Work done already.md`: one run over 1,379 HSC
Physics questions (capped at "the first 150"), and one over a 300-question mixed
BUET paper. Mathematics only ever appeared inside that mixed paper, which is why
it ended up with 16 topics for 170 skills (9.4 topics per 100 skills) against
Chemistry's 23.1 and Physics' 18.9 - and why reading the real Math corpus kept
turning up whole chapters with nowhere to file them (Permutations and
Combinations; Functions and Graphs - both genuine syllabus chapters).

This script replaces that vocabulary with one anchored to the 51 syllabus
chapters: 21 Physics, 10 Chemistry, 20 Higher Mathematics.

Structure
---------
    course  = subject                    (3)
    section = syllabus chapter           (51)
    topic   = sub-topic within a chapter  (see TOPIC counts printed at the end)

Nothing in any `tuples.json` is edited. Every one of the 120 legacy/rebuild topic
codes is remapped through `topic_aliases`, which `build_from_ontology.py` already
applies when compiling - so both the legacy ontology and the in-progress rebuild
land in real syllabus chapters with no source-data migration at all.

Usage
-----
    # write a proposal next to the current config and report the impact
    python Backend/tree_data/build_syllabus_config.py

    # overwrite the live config once the proposal has been reviewed
    python Backend/tree_data/build_syllabus_config.py --out Backend/tree_data/ontology_config.json

Then validate BOTH ontologies before regenerating anything:
    python Backend/tree_data/build_from_ontology.py --source-dir Backend/tree_data/ontology_source --config <cfg> --report-only
    python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild --config <cfg> --report-only
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# The syllabus. (course_id, course_title, course_title_bn, subject) -> chapters
# Each chapter: (section_id, chapter_title_en, chapter_title_bn, [(topic_code, topic_label), ...])
# ---------------------------------------------------------------------------

PHYSICS = [
    ("phy1_ch01_measurement", "Physical World and Measurement", "ভৌতজগত ও পরিমাপ", [
        ("PHY1_MEASUREMENT_UNITS", "Units and Measurement"),
        ("PHY1_DIMENSIONS", "Dimensional Analysis"),
        ("PHY1_ERRORS", "Errors and Significant Figures"),
    ]),
    ("phy1_ch02_vector", "Vector", "ভেক্টর", [
        ("PHY1_VECTOR_ALGEBRA", "Vector Addition and Resolution"),
        ("PHY1_VECTOR_PRODUCTS", "Scalar and Vector Products"),
        ("PHY1_VECTOR_CALCULUS", "Vector Differentiation and Gradient"),
    ]),
    ("phy1_ch03_kinematics", "Dynamics (Kinematics)", "গতিবিদ্যা", [
        ("PHY1_KINEMATICS", "Motion in a Straight Line"),
        ("PHY1_PROJECTILE", "Projectile Motion"),
        ("PHY1_RELATIVE_MOTION", "Relative Velocity"),
    ]),
    ("phy1_ch04_newtonian", "Newtonian Mechanics", "নিউটনীয় বলবিদ্যা", [
        ("PHY1_NEWTON_LAWS", "Newton's Laws of Motion"),
        ("PHY1_MOMENTUM", "Momentum, Impulse and Collisions"),
        ("PHY1_FRICTION", "Friction"),
        ("PHY1_CIRCULAR_MOTION", "Circular Motion"),
        ("PHY1_ROTATIONAL", "Rotational Motion and Angular Momentum"),
    ]),
    ("phy1_ch05_work_energy", "Work, Energy and Power", "কাজ, শক্তি ও ক্ষমতা", [
        ("PHY1_WORK_ENERGY", "Work and Energy"),
        ("PHY1_ENERGY_CONSERVATION", "Conservation of Energy"),
        ("PHY1_POWER", "Power and Efficiency"),
    ]),
    ("phy1_ch06_gravitation", "Gravitation and Gravity", "মহাকর্ষ ও অভিকর্ষ", [
        ("PHY1_GRAVITATION_LAW", "Newton's Law of Gravitation"),
        ("PHY1_GRAVITY_FIELD", "Acceleration due to Gravity and Gravitational Field"),
        ("PHY1_SATELLITE", "Satellites and Escape Velocity"),
    ]),
    ("phy1_ch07_matter", "Structural Properties of Matter", "পদার্থের গাঠনিক ধর্ম", [
        ("PHY1_ELASTICITY", "Elasticity and Hooke's Law"),
        ("PHY1_FLUID_STATICS", "Fluid Pressure and Buoyancy"),
        ("PHY1_SURFACE_TENSION", "Surface Tension and Capillarity"),
        ("PHY1_VISCOSITY", "Viscosity and Fluid Flow"),
        ("PHY1_SOLID_BONDING", "Bonding and Structure of Solids"),
    ]),
    ("phy1_ch08_periodic", "Periodic Motion", "পর্যাবৃত্ত গতি", [
        ("PHY1_SHM", "Simple Harmonic Motion"),
        ("PHY1_PENDULUM", "Pendulum and Spring Oscillations"),
        ("PHY1_SHM_ENERGY", "Energy in Simple Harmonic Motion"),
    ]),
    ("phy1_ch09_wave", "Wave", "তরঙ্গ", [
        ("PHY1_WAVE_BASICS", "Wave Motion and Its Parameters"),
        ("PHY1_WAVE_EQUATION", "Progressive Wave Equation"),
        ("PHY1_SUPERPOSITION", "Superposition, Stationary Waves and Beats"),
        ("PHY1_SOUND", "Sound Waves and the Doppler Effect"),
    ]),
    ("phy1_ch10_gas", "Ideal Gas and Kinetic Theory", "আদর্শ গ্যাস ও গ্যাসের গতিতত্ত্ব", [
        ("PHY1_GAS_LAWS", "Ideal Gas Laws"),
        ("PHY1_KINETIC_THEORY", "Kinetic Theory of Gases"),
        ("PHY1_MOLECULAR_SPEED", "Molecular Speeds and Degrees of Freedom"),
    ]),
    ("phy2_ch01_thermo", "Thermodynamics", "তাপগতিবিদ্যা", [
        ("PHY2_HEAT_TEMPERATURE", "Heat, Temperature and Calorimetry"),
        ("PHY2_THERMO_LAWS", "Laws of Thermodynamics"),
        ("PHY2_HEAT_ENGINE", "Heat Engines and Entropy"),
    ]),
    ("phy2_ch02_electrostatics", "Static Electricity", "স্থির তড়িৎ", [
        ("PHY2_COULOMB", "Coulomb's Law and Electric Field"),
        ("PHY2_GAUSS", "Gauss's Law and Electric Potential"),
        ("PHY2_CAPACITOR", "Capacitance and Dielectrics"),
    ]),
    ("phy2_ch03_current", "Current Electricity", "চল তড়িৎ", [
        ("PHY2_OHM", "Current, Resistance and Ohm's Law"),
        ("PHY2_CIRCUITS", "DC Circuits and Kirchhoff's Laws"),
        ("PHY2_CELLS", "Cells, EMF and Internal Resistance"),
        ("PHY2_METER_BRIDGE", "Measuring Instruments and Bridges"),
    ]),
    ("phy2_ch04_magnetism", "Magnetic Effect of Current and Magnetism",
     "তড়িৎ প্রবাহের চৌম্বক ক্রিয়া ও চুম্বকত্ব", [
        ("PHY2_MAGNETIC_FIELD", "Magnetic Field of a Current"),
        ("PHY2_MAGNETIC_FORCE", "Force on Currents and Moving Charges"),
        ("PHY2_MAGNETIC_MATERIALS", "Magnetic Properties of Materials"),
    ]),
    ("phy2_ch05_induction", "Electromagnetic Induction and Alternating Current",
     "তড়িৎ চৌম্বকীয় আবেশ ও পরিবর্তী প্রবাহ", [
        ("PHY2_INDUCTION", "Electromagnetic Induction and Faraday's Law"),
        ("PHY2_INDUCTANCE", "Self and Mutual Inductance"),
        ("PHY2_AC_CIRCUITS", "Alternating Current Circuits"),
        ("PHY2_TRANSFORMER", "Transformers and Power Transmission"),
    ]),
    ("phy2_ch06_geom_optics", "Geometrical Optics", "জ্যামিতিক আলোকবিজ্ঞান", [
        ("PHY2_REFLECTION", "Reflection and Mirrors"),
        ("PHY2_REFRACTION", "Refraction and Lenses"),
        ("PHY2_OPTICAL_INSTRUMENTS", "Optical Instruments"),
    ]),
    ("phy2_ch07_phys_optics", "Physical Optics", "ভৌত আলোকবিজ্ঞান", [
        ("PHY2_INTERFERENCE", "Interference of Light"),
        ("PHY2_DIFFRACTION", "Diffraction"),
        ("PHY2_POLARISATION", "Polarisation"),
    ]),
    ("phy2_ch08_modern", "Introduction to Modern Physics", "আধুনিক পদার্থবিজ্ঞানের সূচনা", [
        ("PHY2_RELATIVITY", "Special Relativity"),
        ("PHY2_PHOTOELECTRIC", "Photoelectric Effect and Photons"),
        ("PHY2_XRAY", "X-rays"),
        ("PHY2_MATTER_WAVES", "Matter Waves and the Uncertainty Principle"),
    ]),
    ("phy2_ch09_atomic_nuclear", "Atomic Model and Nuclear Physics",
     "পরমাণুর মডেল ও নিউক্লিয়ার পদার্থবিজ্ঞান", [
        ("PHY2_ATOMIC_MODELS", "Atomic Models and Spectra"),
        ("PHY2_NUCLEUS", "Nuclear Structure and Binding Energy"),
        ("PHY2_RADIOACTIVITY", "Radioactivity and Decay"),
        ("PHY2_FISSION_FUSION", "Fission, Fusion and Reactors"),
    ]),
    ("phy2_ch10_semiconductor", "Semiconductor and Electronics", "সেমিকন্ডাক্টর ও ইলেকট্রনিক্স", [
        ("PHY2_SEMICONDUCTOR", "Semiconductors and Doping"),
        ("PHY2_DIODE", "Diodes and Rectification"),
        ("PHY2_TRANSISTOR", "Transistors and Amplifiers"),
        ("PHY2_LOGIC_GATES", "Digital Logic Gates"),
    ]),
    ("phy2_ch11_astronomy", "Astronomy", "জ্যোতির্বিজ্ঞান", [
        ("PHY2_SOLAR_SYSTEM", "Solar System and Stars"),
        ("PHY2_COSMOLOGY", "The Universe and Cosmology"),
    ]),
]

CHEMISTRY = [
    ("che1_ch01_lab", "Safe Use of the Laboratory", "ল্যাবরেটরির নিরাপদ ব্যবহার", [
        ("CHE1_LAB_APPARATUS", "Laboratory Apparatus and Glassware"),
        ("CHE1_LAB_SAFETY", "Hazards, Safety Symbols and First Aid"),
        ("CHE1_LAB_SEPARATION", "Separation and Purification Techniques"),
        ("CHE1_LAB_REAGENTS", "Cleaning Agents and Drying Agents"),
    ]),
    ("che1_ch02_qualitative", "Qualitative Chemistry", "গুণগত রসায়ন", [
        ("CHE1_FLAME_TEST", "Flame Tests and Emission Colours"),
        ("CHE1_CATION_ANALYSIS", "Group Analysis of Cations"),
        ("CHE1_ANION_ANALYSIS", "Identification of Anions"),
        ("CHE1_CONFIRMATORY", "Confirmatory Tests and Reagents"),
        ("CHE1_SOLUBILITY_RULES", "Solubility Rules and Precipitation"),
    ]),
    ("che1_ch03_periodic_bonding", "Periodic Properties of Elements and Chemical Bonding",
     "মৌলের পর্যায়বৃত্তিক ধর্ম ও রাসায়নিক বন্ধন", [
        ("CHE1_ATOMIC_STRUCTURE", "Atomic Structure and Quantum Numbers"),
        ("CHE1_ELECTRON_CONFIG", "Electron Configuration"),
        ("CHE1_ATOMIC_SPECTRA", "Atomic Spectra and the Electromagnetic Spectrum"),
        ("CHE1_NUCLEAR_CHEM", "Nuclear Chemistry and Radioactivity"),
        ("CHE1_PERIODIC_TRENDS", "Periodic Properties and Trends"),
        ("CHE1_IONIC_BOND", "Ionic Bonding and Lattices"),
        ("CHE1_COVALENT_BOND", "Covalent Bonding, Hybridisation and Molecular Shape"),
        ("CHE1_INTERMOLECULAR", "Intermolecular Forces"),
        ("CHE1_COORDINATION", "Coordination Compounds"),
        ("CHE1_TRANSITION", "Transition Elements"),
        ("CHE1_SOLID_STATE", "Solid State and Crystal Structure"),
    ]),
    ("che1_ch04_chemical_change", "Chemical Changes", "রাসায়নিক পরিবর্তন", [
        ("CHE1_REACTION_RATE", "Rate of Reaction and Chemical Kinetics"),
        ("CHE1_CATALYSIS", "Catalysis"),
        ("CHE1_EQUILIBRIUM", "Chemical Equilibrium"),
        ("CHE1_THERMOCHEM", "Thermochemistry and Enthalpy"),
        ("CHE1_ACID_BASE", "Acids, Bases and pH"),
        ("CHE1_BUFFER", "Buffers and Salt Hydrolysis"),
        ("CHE1_REDOX", "Oxidation, Reduction and Oxidation Number"),
    ]),
    ("che1_ch05_applied", "Applied Chemistry", "কর্মমুখী রসায়ন", [
        ("CHE1_APPLIED_MATERIALS", "Everyday Materials and Consumer Products"),
        ("CHE1_APPLIED_PROCESS", "Applied Industrial Processes"),
    ]),
    ("che2_ch01_environmental", "Environmental Chemistry", "পরিবেশ রসায়ন", [
        # গ্যাসীয় অবস্থা sits in this chapter in the NCTB syllabus - the gas laws are
        # taught here as the groundwork for studying the atmosphere.
        ("CHE2_GAS_LAWS", "Gaseous State and Gas Laws"),
        ("CHE2_KINETIC_THEORY", "Kinetic Theory and Real Gases"),
        ("CHE2_ATMOSPHERE", "Atmosphere and Air Pollution"),
        ("CHE2_ACID_RAIN", "Acid Rain and the Greenhouse Effect"),
        ("CHE2_WATER_SOIL", "Water and Soil Quality"),
        ("CHE2_GREEN_CHEM", "Green Chemistry"),
    ]),
    ("che2_ch02_organic", "Organic Chemistry", "জৈব রসায়ন", [
        ("CHE2_ORG_BASICS", "Bonding, Isomerism and Reactive Intermediates"),
        ("CHE2_ORG_NOMENCLATURE", "Nomenclature and Homologous Series"),
        ("CHE2_ORG_HYDROCARBON", "Alkanes, Alkenes and Alkynes"),
        ("CHE2_ORG_AROMATIC", "Aromatic Compounds and Substitution"),
        ("CHE2_ORG_HALIDE", "Halogen Derivatives"),
        ("CHE2_ORG_ALCOHOL", "Alcohols, Phenols and Ethers"),
        ("CHE2_ORG_CARBONYL", "Aldehydes and Ketones"),
        ("CHE2_ORG_ACID", "Carboxylic Acids and Their Derivatives"),
        ("CHE2_ORG_AMINE", "Amines and Nitrogen Compounds"),
        ("CHE2_ORG_STEREO", "Stereochemistry"),
        ("CHE2_ORG_POLYMER", "Polymers and Plastics"),
        ("CHE2_BIOMOLECULE", "Biomolecules"),
    ]),
    ("che2_ch03_quantitative", "Quantitative Chemistry", "পরিমাণগত রসায়ন", [
        ("CHE2_MOLE", "Mole Concept and Stoichiometry"),
        ("CHE2_FORMULA", "Empirical and Molecular Formula"),
        ("CHE2_SOLUTION_CONC", "Solutions and Concentration"),
        ("CHE2_TITRATION", "Titrimetric (Volumetric) Analysis"),
        ("CHE2_GRAVIMETRIC", "Gravimetric Analysis"),
    ]),
    ("che2_ch04_electrochem", "Electrochemistry", "তড়িৎ রসায়ন", [
        ("CHE2_ELECTROLYSIS", "Electrolysis and Faraday's Laws"),
        ("CHE2_GALVANIC", "Galvanic Cells and Electrode Potential"),
        ("CHE2_BATTERY", "Batteries and Corrosion"),
    ]),
    ("che2_ch05_economic", "Economic Chemistry", "অর্থনৈতিক রসায়ন", [
        ("CHE2_INDUSTRIAL", "Industrial Chemical Processes"),
        ("CHE2_METALLURGY", "Ores, Minerals and Metallurgy"),
        ("CHE2_ALLOY", "Alloys and Engineering Materials"),
        ("CHE2_DESCRIPTIVE", "Descriptive Inorganic Chemistry"),
    ]),
]

MATHEMATICS = [
    ("mat1_ch01_matrix", "Matrices and Determinants", "ম্যাট্রিক্স ও নির্ণায়ক", [
        ("MAT1_MATRIX_ALGEBRA", "Matrix Operations"),
        ("MAT1_DETERMINANT", "Determinants and Their Properties"),
        ("MAT1_INVERSE", "Inverse Matrices and Linear Systems"),
    ]),
    ("mat1_ch02_vector", "Vector", "ভেক্টর", [
        ("MAT1_VECTOR_ALGEBRA", "Vector Algebra and Components"),
        ("MAT1_VECTOR_PRODUCT", "Scalar and Vector Products"),
        ("MAT1_VECTOR_GEOMETRY", "Vector Applications to Geometry"),
    ]),
    ("mat1_ch03_line", "Straight Line", "সরলরেখা", [
        ("MAT1_LINE_BASICS", "Coordinates, Distance and Slope"),
        ("MAT1_LINE_EQUATION", "Equations of a Straight Line"),
        ("MAT1_LINE_PAIR", "Angles, Distances and Pairs of Lines"),
        ("MAT1_POLAR", "Polar Coordinates"),
    ]),
    ("mat1_ch04_circle", "Circle", "বৃত্ত", [
        ("MAT1_CIRCLE_EQUATION", "Equation of a Circle"),
        ("MAT1_CIRCLE_TANGENT", "Tangents and Normals to a Circle"),
        ("MAT1_CIRCLE_PAIR", "Two Circles and Common Chords"),
    ]),
    ("mat1_ch05_permcomb", "Permutation and Combination", "বিন্যাস ও সমাবেশ", [
        ("MAT1_PERMUTATION", "Permutations"),
        ("MAT1_COMBINATION", "Combinations"),
        ("MAT1_COUNTING_APP", "Applications of Counting"),
    ]),
    ("mat1_ch06_trig_ratio", "Trigonometric Ratios", "ত্রিকোণমিতিক অনুপাত", [
        ("MAT1_TRIG_RATIOS", "Trigonometric Ratios and Identities"),
        ("MAT1_TRIG_ANGLES", "Ratios of Standard and Associated Angles"),
    ]),
    ("mat1_ch07_compound_angle", "Trigonometric Ratios of Associated and Compound Angles",
     "সংযুক্ত ও যৌগিক কোণের ত্রিকোণমিতিক অনুপাত", [
        ("MAT1_COMPOUND_ANGLE", "Compound Angle Formulae"),
        ("MAT1_MULTIPLE_ANGLE", "Multiple and Sub-multiple Angles"),
        ("MAT1_SUM_PRODUCT", "Sum-to-Product Transformations"),
        ("MAT1_TRIANGLE_PROPS", "Properties of Triangles"),
    ]),
    ("mat1_ch08_function", "Functions and Graphs of Functions", "ফাংশন ও ফাংশনের লেখচিত্র", [
        ("MAT1_FUNCTION_BASICS", "Functions, Domain and Range"),
        ("MAT1_FUNCTION_COMPOSE", "Composition and Inverse Functions"),
        ("MAT1_FUNCTION_GRAPH", "Graphs of Functions"),
    ]),
    ("mat1_ch09_differentiation", "Differentiation", "অন্তরীকরণ", [
        ("MAT1_LIMIT", "Limits and Continuity"),
        ("MAT1_DERIVATIVE", "Rules of Differentiation"),
        ("MAT1_DERIV_APPLICATION", "Applications of Derivatives"),
    ]),
    ("mat1_ch10_integration", "Integration", "যোগজীকরণ", [
        ("MAT1_INTEGRAL", "Indefinite Integration"),
        ("MAT1_INTEGRAL_DEF", "Definite Integrals"),
        ("MAT1_INTEGRAL_APP", "Areas and Applications of Integration"),
    ]),
    ("mat2_ch01_real_numbers", "Real Numbers and Inequalities", "বাস্তব সংখ্যা ও অসমতা", [
        ("MAT2_REAL_NUMBERS", "Real Numbers and Absolute Value"),
        ("MAT2_INEQUALITY", "Inequalities"),
    ]),
    ("mat2_ch02_linear_prog", "Linear Programming", "যোগাশ্রয়ী প্রোগ্রাম", [
        ("MAT2_LINEAR_PROG", "Linear Programming"),
    ]),
    ("mat2_ch03_complex", "Complex Numbers", "জটিল সংখ্যা", [
        ("MAT2_COMPLEX_ALGEBRA", "Complex Number Algebra"),
        ("MAT2_COMPLEX_POLAR", "Polar Form and De Moivre's Theorem"),
        ("MAT2_COMPLEX_ROOTS", "Roots of Unity"),
    ]),
    ("mat2_ch04_polynomial", "Polynomial and Polynomial Equations", "বহুপদী ও বহুপদী সমীকরণ", [
        ("MAT2_POLYNOMIAL", "Polynomials and the Remainder Theorem"),
        ("MAT2_POLY_ROOTS", "Roots of Polynomial Equations"),
        ("MAT2_EXPONENTIAL_EQ", "Exponential and Logarithmic Equations"),
    ]),
    ("mat2_ch05_binomial", "Binomial Expansion", "দ্বিপদী বিস্তৃতি", [
        ("MAT2_BINOMIAL", "Binomial Expansion"),
    ]),
    ("mat2_ch06_conic", "Conics", "কণিক", [
        ("MAT2_PARABOLA", "Parabola"),
        ("MAT2_ELLIPSE", "Ellipse"),
        ("MAT2_HYPERBOLA", "Hyperbola"),
    ]),
    ("mat2_ch07_inverse_trig", "Inverse Trigonometric Functions and Trigonometric Equations",
     "বিপরীত ত্রিকোণমিতিক ফাংশন ও ত্রিকোণমিতিক সমীকরণ", [
        ("MAT2_INVERSE_TRIG", "Inverse Trigonometric Functions"),
        ("MAT2_TRIG_EQUATION", "Trigonometric Equations"),
    ]),
    ("mat2_ch08_statics", "Statics", "স্থিতিবিদ্যা", [
        ("MAT2_STATICS_FORCE", "Forces and Equilibrium"),
        ("MAT2_STATICS_FRICTION", "Friction and Moments"),
    ]),
    ("mat2_ch09_plane_motion", "Motion of Particles in a Plane", "সমতলে বস্তুকণার গতি", [
        ("MAT2_PLANE_MOTION", "Motion in a Plane"),
        ("MAT2_PROJECTILE", "Projectile Motion"),
    ]),
    ("mat2_ch10_probability", "Measures of Dispersion and Probability", "বিস্তার পরিমাপ ও সম্ভাবনা", [
        ("MAT2_DISPERSION", "Measures of Dispersion"),
        ("MAT2_PROBABILITY", "Probability"),
    ]),
]

COURSES = [
    ("physics", "Physics", "পদার্থবিজ্ঞান", "Physics", PHYSICS),
    ("chemistry", "Chemistry", "রসায়ন", "Chemistry", CHEMISTRY),
    ("higher_math", "Higher Mathematics", "উচ্চতর গণিত", "Mathematics", MATHEMATICS),
]

# ---------------------------------------------------------------------------
# Every topic code that appears in the legacy ontology or the rebuild, mapped to
# its syllabus home. A code maps to exactly one topic; where a code genuinely
# spans two syllabus topics it goes to the dominant one and is listed in
# SPLIT_CANDIDATES below for later skill-level retagging.
# ---------------------------------------------------------------------------

ALIASES = {
    # ---- Chemistry -------------------------------------------------------
    "CHEM_LAB": "CHE1_LAB_APPARATUS",
    "CHE_QUAL": "CHE1_CATION_ANALYSIS",
    "CHEM_QUALITATIVE": "CHE1_CATION_ANALYSIS",
    "CHE_ATOMIC": "CHE1_ATOMIC_STRUCTURE",
    "CHEM_ATOMIC": "CHE1_ATOMIC_STRUCTURE",
    "CHEM_AT": "CHE1_ATOMIC_STRUCTURE",
    "CHEM_SPEC": "CHE1_ATOMIC_SPECTRA",
    "CHEM_NUCLEAR": "CHE1_NUCLEAR_CHEM",
    "CHEM_PERIODIC": "CHE1_PERIODIC_TRENDS",
    "CHEM_PER": "CHE1_PERIODIC_TRENDS",
    "CHE_BONDING": "CHE1_COVALENT_BOND",
    "CHEM_BONDING": "CHE1_COVALENT_BOND",
    "CHEM_BOND": "CHE1_COVALENT_BOND",
    "CHEM_SOLID": "CHE1_SOLID_STATE",
    "CHE_COORD": "CHE1_COORDINATION",
    "CHEM_COORD": "CHE1_COORDINATION",
    "CHEM_DBLOCK": "CHE1_TRANSITION",
    "CHE_GASLAWS": "CHE2_GAS_LAWS",
    "CHEM_GASLAW": "CHE2_GAS_LAWS",
    "CHEM_GAS": "CHE2_GAS_LAWS",
    "CHEM_KIN": "CHE1_REACTION_RATE",
    "CHEM_KINETICS": "CHE1_REACTION_RATE",
    "CHEM_CAT": "CHE1_CATALYSIS",
    "CHE_EQUILIBRIUM": "CHE1_EQUILIBRIUM",
    "CHEM_EQUILIBRIUM": "CHE1_EQUILIBRIUM",
    "CHEM_EQ": "CHE1_EQUILIBRIUM",
    "CHE_THERMOCHEM": "CHE1_THERMOCHEM",
    "CHE_ACIDBASE": "CHE1_ACID_BASE",
    "CHEM_ACIDBASE": "CHE1_ACID_BASE",
    "CHEM_AB": "CHE1_ACID_BASE",
    "CHEM_REDOX": "CHE1_REDOX",
    "CHEM_ENV": "CHE2_ATMOSPHERE",
    "CHE_ORGANIC": "CHE2_ORG_HYDROCARBON",
    "CHEM_ORGANIC": "CHE2_ORG_HYDROCARBON",
    "CHEM_ORG": "CHE2_ORG_HYDROCARBON",
    "CHEM_NOM": "CHE2_ORG_NOMENCLATURE",
    "CHEM_STEREO": "CHE2_ORG_STEREO",
    "CHE_BIOMOLECULE": "CHE2_BIOMOLECULE",
    "CHE_STOICHIOMETRY": "CHE2_MOLE",
    "CHEM_STOICH": "CHE2_MOLE",
    "CHEM_MOLE": "CHE2_MOLE",
    "CHEM_SOLUTION": "CHE2_SOLUTION_CONC",
    "CHEM_ANALYTICAL": "CHE2_TITRATION",
    "CHE_ELECTROCHEM": "CHE2_GALVANIC",
    "CHEM_ELECTROCHEM": "CHE2_GALVANIC",
    "CHEM_DESCRIPTIVE": "CHE2_DESCRIPTIVE",

    # ---- Mathematics -----------------------------------------------------
    "MAT_MATRIX": "MAT1_MATRIX_ALGEBRA",
    "MATH_MAT": "MAT1_MATRIX_ALGEBRA",
    "MATH_MECH": "MAT1_VECTOR_ALGEBRA",
    "MAT_COORD_LINE": "MAT1_LINE_EQUATION",
    "MATH_LINE": "MAT1_LINE_EQUATION",
    "MATH_COORD": "MAT1_LINE_BASICS",
    "MATH_GEOM": "MAT1_LINE_BASICS",
    "MAT_COORD_CONIC": "MAT1_CIRCLE_EQUATION",
    "MATH_CONIC": "MAT2_PARABOLA",
    "MAT_PERMCOMB": "MAT1_PERMUTATION",
    "MAT_TRIG": "MAT1_COMPOUND_ANGLE",
    "MATH_TRIG": "MAT1_TRIG_RATIOS",
    "MAT_FUNCTION": "MAT1_FUNCTION_BASICS",
    "MAT_CALC_DIFF": "MAT1_DERIVATIVE",
    "MATH_LIMIT": "MAT1_LIMIT",
    "MATH_CALC": "MAT1_DERIVATIVE",
    "MAT_CALC_INTEG": "MAT1_INTEGRAL",
    "MATH_INTEG": "MAT1_INTEGRAL",
    "MAT_COMPLEX": "MAT2_COMPLEX_ALGEBRA",
    "MATH_COMPLEX": "MAT2_COMPLEX_ALGEBRA",
    "MATH_CX": "MAT2_COMPLEX_ALGEBRA",
    "MAT_EQTHEORY": "MAT2_POLY_ROOTS",
    "MATH_POLY": "MAT2_POLY_ROOTS",
    "MAT_ALGEBRA": "MAT2_EXPONENTIAL_EQ",
    "MATH_ALG": "MAT2_EXPONENTIAL_EQ",
    "MAT_INVTRIG": "MAT2_INVERSE_TRIG",
    "MAT_STATICS": "MAT2_STATICS_FORCE",
    "MATH_STATICS": "MAT2_STATICS_FORCE",
    "MAT_DYNAMICS": "MAT2_PLANE_MOTION",
    "MATH_DYNAMICS": "MAT2_PLANE_MOTION",

    # ---- Physics ---------------------------------------------------------
    "PHY_UNITS": "PHY1_MEASUREMENT_UNITS",
    "PHY_MEAS": "PHY1_MEASUREMENT_UNITS",
    "PHY_VEC": "PHY1_VECTOR_ALGEBRA",
    "PHY_DYNAMICS": "PHY1_KINEMATICS",
    "PHY_PROJ": "PHY1_PROJECTILE",
    "PHY_NEWTON": "PHY1_NEWTON_LAWS",
    "PHY_NEWT": "PHY1_NEWTON_LAWS",
    "PHY_CIRC": "PHY1_CIRCULAR_MOTION",
    "PHY_ROTATION": "PHY1_ROTATIONAL",
    "PHY_ROT": "PHY1_ROTATIONAL",
    "PHY_WORK_ENERGY": "PHY1_WORK_ENERGY",
    "PHY_WORK": "PHY1_WORK_ENERGY",
    "PHY_GRAVITATION": "PHY1_GRAVITATION_LAW",
    "PHY_GRAV": "PHY1_GRAVITATION_LAW",
    "PHY_ELASTICITY": "PHY1_ELASTICITY",
    "PHY_FLUID": "PHY1_SURFACE_TENSION",
    "PHY_SOLID": "PHY1_SOLID_BONDING",
    "PHY_SHM": "PHY1_SHM",
    "PHY_OSC": "PHY1_SHM",
    "PHY_WAVE": "PHY1_WAVE_BASICS",
    "PHY_KINETIC": "PHY1_KINETIC_THEORY",
    "PHY_KTG": "PHY1_KINETIC_THEORY",
    "PHY_THERMO": "PHY2_THERMO_LAWS",
    "PHY_ELECTROSTATICS": "PHY2_COULOMB",
    "PHY_ELEC": "PHY2_COULOMB",
    "PHY_CAP": "PHY2_CAPACITOR",
    "PHY_CURRENT": "PHY2_OHM",
    "PHY_CUR": "PHY2_OHM",
    "PHY_CIRCUIT": "PHY2_CIRCUITS",
    "PHY_MAGNETISM": "PHY2_MAGNETIC_FIELD",
    "PHY_MAG": "PHY2_MAGNETIC_FIELD",
    "PHY_EM": "PHY2_INDUCTION",
    "PHY_OPT": "PHY2_REFRACTION",
    "PHY_OPTICS": "PHY2_INTERFERENCE",
    "PHY_OPTICS_WAVE": "PHY2_INTERFERENCE",
    "PHY_MODERN": "PHY2_PHOTOELECTRIC",
    "PHY_MOD": "PHY2_PHOTOELECTRIC",
    "PHY_XRAY": "PHY2_XRAY",
    "PHY_AT": "PHY2_ATOMIC_MODELS",
    "PHY_NUCLEAR": "PHY2_NUCLEUS",
    "PHY_NUC": "PHY2_NUCLEUS",
    "PHY_SEMICONDUCTOR": "PHY2_SEMICONDUCTOR",
    "PHY_SEMICOND": "PHY2_SEMICONDUCTOR",
    "PHY_SEMI": "PHY2_SEMICONDUCTOR",
}

# Old codes whose skills genuinely straddle two syllabus topics. They are mapped
# to the dominant one above; splitting them properly needs skill-level retagging,
# not an alias.
SPLIT_CANDIDATES = {
    "CHE_ORGANIC": "154 rebuild skills spanning every organic sub-topic (hydrocarbons, aromatics, alcohols, carbonyls, acids, amines, polymers). Currently all land in CHE2_ORG_HYDROCARBON.",
    "MAT_COORD_CONIC": "circles (HM1 Ch4) and the other conics (HM2 Ch6) share one code. Currently all land in MAT1_CIRCLE_EQUATION.",
    "MAT_TRIG": "basic ratios (HM1 Ch6) and compound/multiple angles (HM1 Ch7) share one code. Currently all land in MAT1_COMPOUND_ANGLE.",
    "CHEM_REDOX": "redox fundamentals (Chem 1st Ch4) and electrochemical application (Chem 2nd Ch4) share one code. Currently all land in CHE1_REDOX.",
    "CHEM_ENV": "air, water/soil and green chemistry share one code. Currently all land in CHE2_ATMOSPHERE.",
    "MATH_MECH": "vectors, statics and dynamics share one code. Currently all land in MAT1_VECTOR_ALGEBRA.",
    "PHY_FLUID": "fluid statics, surface tension and viscosity share one code.",
    "MAT_COORD_LINE": "line basics, equations, pairs of lines and polar coordinates share one code.",
}

README = [
    "Editorial layer over the raw ontology (ontology_source/). Everything here is a",
    "human decision that cannot be derived from the source data.",
    "",
    "GENERATED by Backend/tree_data/build_syllabus_config.py - edit that script and",
    "re-run, rather than editing this file by hand. Re-run with:",
    "    python Backend/tree_data/build_syllabus_config.py --out Backend/tree_data/ontology_config.json",
    "then recompile:",
    "    python Backend/tree_data/build_from_ontology.py --out-dir Backend/tree_data --force",
    "",
    "topic_aliases : raw topic_code -> canonical topic_code. The raw codes come from",
    "  the original ad-hoc ontology runs and from the in-progress corpus rebuild;",
    "  they are remapped here onto the syllabus vocabulary so no tuples.json has to",
    "  be edited. See the script's SPLIT_CANDIDATES for codes that really need",
    "  skill-level retagging rather than a 1:1 alias.",
    "topic_labels  : canonical topic_code -> display label.",
    "courses       : one course per subject; ONE SECTION PER SYLLABUS CHAPTER",
    "  (51 chapters: 21 Physics, 10 Chemistry, 20 Higher Mathematics), each holding",
    "  the sub-topics of that chapter. Section order is the syllabus chapter order.",
    "",
    "Any canonical topic not listed under a section is still ingested, but will not",
    "appear in the catalog. The build reports those.",
]


def build() -> dict:
    labels: dict[str, str] = {}
    courses = []
    for course_id, title, title_bn, subject, chapters in COURSES:
        sections = []
        for section_id, ch_en, ch_bn, topics in chapters:
            for code, label in topics:
                if code in labels:
                    raise SystemExit(f"duplicate topic code: {code}")
                labels[code] = label
            sections.append({"id": section_id, "title": ch_en, "title_bn": ch_bn,
                             "topics": [c for c, _ in topics]})
        courses.append({"id": course_id, "title": title, "title_bn": title_bn,
                        "subject": subject, "sections": sections})
    return {"_README": README, "topic_aliases": dict(sorted(ALIASES.items())),
            "topic_labels": labels, "courses": courses}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=REPO / "Backend/tree_data/ontology_config.syllabus.json")
    args = ap.parse_args()

    cfg = build()

    # --- coverage check against every topic code actually in use -------------
    in_use: collections.Counter = collections.Counter()
    for path in [REPO / "Ontology/tuples.json",
                 REPO / "Ontology/full_corpus_rebuild/tuples.json"]:
        if path.is_file():
            for x in json.loads(path.read_text(encoding="utf-8")):
                in_use[x["topicKey"]] += 1

    known = set(cfg["topic_labels"])
    unmapped = sorted(c for c in in_use if c not in ALIASES and c not in known)
    bad_targets = sorted({v for v in ALIASES.values() if v not in known})

    args.out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n_sections = sum(len(c["sections"]) for c in cfg["courses"])
    try:
        shown = args.out.resolve().relative_to(REPO).as_posix()
    except ValueError:
        shown = args.out.as_posix()
    print(f"wrote {shown}")
    print(f"  courses   : {len(cfg['courses'])}")
    print(f"  sections  : {n_sections}   (one per syllabus chapter)")
    print(f"  topics    : {len(cfg['topic_labels'])}")
    print(f"  aliases   : {len(ALIASES)}   (old codes remapped)")
    for c in cfg["courses"]:
        tn = sum(len(s["topics"]) for s in c["sections"])
        print(f"    {c['subject']:13} {len(c['sections']):>3} chapters, {tn:>3} topics")

    if bad_targets:
        print(f"\n  ERROR alias targets that are not real topics: {bad_targets}")
    if unmapped:
        print(f"\n  ERROR topic codes in use with no alias ({len(unmapped)}):")
        for c in unmapped:
            print(f"    {c}  ({in_use[c]} skills)")
    if not bad_targets and not unmapped:
        print(f"\n  OK every one of the {len(in_use)} topic codes in use maps to a syllabus topic")

    filled = {ALIASES[c] for c in in_use if c in ALIASES}
    empty = sorted(known - filled)
    print(f"\n  topics with skills today : {len(filled)}")
    print(f"  topics still empty       : {len(empty)}  (fill as extraction continues)")
    print(f"\n  codes needing a later skill-level split: {len(SPLIT_CANDIDATES)}")
    for code, why in SPLIT_CANDIDATES.items():
        print(f"    {code:18} {why[:88]}")


if __name__ == "__main__":
    main()
