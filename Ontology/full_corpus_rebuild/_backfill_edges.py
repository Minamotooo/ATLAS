"""
_backfill_edges.py
------------------
Add the prerequisite edges the extraction pass never proposed, one topic at a
time. See `prereq_sparsity_diagnosis.md` for why they are missing.

Each entry in EDGES is a hand-made judgement: "before a learner can hold this
skill, what must they already hold?", answered against the whole accumulated
ontology rather than against the source record. That is the question the original
prompt failed to ask.

Run from the repo root:
    python Ontology/full_corpus_rebuild/_backfill_edges.py --dry-run
    python Ontology/full_corpus_rebuild/_backfill_edges.py --apply

Safe to re-run: existing edges are never duplicated. The script refuses to write
if any edge would introduce a cycle, or if any skillId does not exist.
Originals are in `_prefix_backup/`.

Verify after applying:
    python Ontology/full_corpus_rebuild/_edge_coverage.py --by-topic
    python Backend/tree_data/build_from_ontology.py --source-dir Ontology/full_corpus_rebuild \
        --config Backend/tree_data/ontology_config.json --report-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent

# dependent skillId -> [prerequisite skillIds]
# Batch 1: CHEM_DESCRIPTIVE (24 skills, was 100% isolated).
EDGES: dict[str, list[str]] = {
    # Predicting inorganic products needs solubility rules (precipitation),
    # oxidation numbers and the reactivity series (redox), and the thermal
    # decomposition pattern.
    "CHEM_DESCRIPTIVE0":  ["CHEM_SOLUTION7", "CHEM_REDOX2", "CHEM_REDOX31", "CHEM_REDOX28"],

    # Limewater turning milky then clearing is solubility (CaCO3 vs Ca(HCO3)2)
    # plus the carbonate/hydrogencarbonate equilibrium.
    "CHEM_DESCRIPTIVE10": ["CHEM_SOLUTION7", "CHE_ACIDBASE52"],

    # The divers' helium-oxygen answer presupposes knowing which gases are noble
    # and what they are used for.
    "CHEM_DESCRIPTIVE11": ["CHEM_PERIODIC13", "CHEM_DESCRIPTIVE8"],

    # "Silent killer" is the consequence of CO's haemoglobin complexation.
    "CHEM_DESCRIPTIVE12": ["CHE_COORD5"],

    # Naming an alloy from its composition presupposes knowing the compositions.
    "CHEM_DESCRIPTIVE13": ["CHEM_DESCRIPTIVE2"],

    # HF etching glass presupposes knowing glass contains silica.
    "CHEM_DESCRIPTIVE14": ["CHEM_SOLID4"],
    "CHEM_DESCRIPTIVE15": ["CHEM_PERIODIC13"],

    # Alkali attacking glass: silica is an acidic oxide, and glass contains it.
    "CHEM_DESCRIPTIVE16": ["CHEM_SOLID4", "CHE_ACIDBASE3"],

    # Vigorous alkali-metal/water reaction needs the group identity and the
    # reactivity series.
    "CHEM_DESCRIPTIVE17": ["CHEM_PERIODIC11", "CHEM_REDOX31"],

    # These are all "recall a fact about a named compound" — they presuppose
    # being able to map the trivial/commercial name to a chemical identity.
    "CHEM_DESCRIPTIVE18": ["CHEM_DESCRIPTIVE1"],
    "CHEM_DESCRIPTIVE19": ["CHEM_DESCRIPTIVE1"],
    # (CHEM_NOM6, the ore definition, added in batch 3)
    "CHEM_DESCRIPTIVE3":  ["CHEM_DESCRIPTIVE1", "CHEM_NOM6"],
    "CHEM_DESCRIPTIVE6":  ["CHEM_DESCRIPTIVE1"],
    "CHEM_DESCRIPTIVE7":  ["CHEM_DESCRIPTIVE1"],

    # Physical vs chemical change is judged on the stock examples — rusting and
    # burning — so it rests on knowing those are chemical processes.
    "CHEM_DESCRIPTIVE20": ["CHEM_REDOX45", "CHEM_REDOX27"],

    # Amphoteric metals liberating H2 from hot alkali rests on the amphoteric
    # classification itself.
    "CHEM_DESCRIPTIVE21": ["CHE_ACIDBASE3", "CHE_ACIDBASE4"],

    # Bleaching powder is chlorine's disproportionation in alkali.
    "CHEM_DESCRIPTIVE22": ["CHEM_REDOX25"],

    # Writing the water-gas equation presupposes knowing what water gas is.
    "CHEM_DESCRIPTIVE23": ["CHEM_DESCRIPTIVE9"],

    # The flame-test procedure step presupposes knowing what the test shows.
    "CHEM_DESCRIPTIVE5":  ["CHEM_DESCRIPTIVE4"],

    "CHEM_DESCRIPTIVE8":  ["CHEM_PERIODIC13"],

    # ---------------------------------------------------------------- Batch 2
    # CHEM_SOLID (10 skills, 9 isolated)

    # Ice's hexagonal lattice is a consequence of hydrogen bonding.
    "CHEM_SOLID3":  ["CHE_BONDING25"],
    # Explaining diamond's melting point needs the force-strength ordering first.
    "CHEM_SOLID5":  ["CHE_BONDING43"],
    # Graphite as a lubricant rests on its covalent layered structure and on
    # knowing interlayer forces are weaker than the covalent bonds within a layer.
    "CHEM_SOLID6":  ["CHEM_SOLID9", "CHE_BONDING43"],
    # Colouring glass presupposes knowing the base glass composition.
    "CHEM_SOLID7":  ["CHEM_SOLID4"],
    # Plaster of Paris is a formula-from-common-name recall.
    "CHEM_SOLID8":  ["CHEM_DESCRIPTIVE1"],
    # Graphite/diamond bonding presupposes that carbon is allotropic.
    "CHEM_SOLID9":  ["CHEM_PERIODIC30"],
    # Liquid-crystal structure is read in terms of polar groups and chain flexibility.
    "CHEM_SOLID10": ["CHE_BONDING43"],
    # Sublimation presupposes the state-change vocabulary.
    "CHEM_SOLID11": ["CHE_THERMOCHEM2"],

    # CHEM_LAB (16 skills, 14 isolated)

    # Choosing Pyrex for apparatus rests on what Pyrex is and why it resists heat.
    "CHEM_LAB0":  ["CHEM_SOLID4"],
    # A lab detergent's cleaning action rests on what a detergent is chemically.
    "CHEM_LAB1":  ["CHE_ORGANIC51"],
    # Hazard classes and first aid both rest on what a hazard pictogram is.
    "CHEM_LAB3":  ["CHEM_LAB4"],
    "CHEM_LAB5":  ["CHEM_LAB3"],
    # Glove choice follows from the hazard class being protected against.
    "CHEM_LAB6":  ["CHEM_LAB3"],
    # Chromic acid cleaning presupposes the dichromate species.
    "CHEM_LAB7":  ["CHE_BONDING31"],
    # Reading a burette presupposes recognising one.
    "CHEM_LAB9":  ["CHEM_LAB8"],
    # Solvent choice is a polarity / like-dissolves-like judgement.
    "CHEM_LAB10": ["CHEM_SOLUTION6"],
    # Liquor ammonia as a cleaning agent presupposes knowing what it is.
    "CHEM_LAB11": ["CHE_ACIDBASE6"],
    # Naming the chromatography variant presupposes the general technique.
    "CHEM_LAB13": ["CHEM_LAB12"],
    # CaCl2 failing to dry ammonia is ammonia acting as a ligand.
    "CHEM_LAB15": ["CHE_COORD7"],

    # CHE_QUAL (22 skills, 18 isolated)

    # Group classification builds on the group-reagent recall.
    "CHE_QUAL19": ["CHE_QUAL2"],
    # Writing a confirmatory-test equation needs the reagent and the solubility rules.
    "CHE_QUAL13": ["CHE_QUAL2", "CHEM_SOLUTION7"],
    # Reading a test result back to an ion presupposes knowing the test reactions.
    "CHE_QUAL16": ["CHE_QUAL13"],
    # Sulfide precipitate colours sit inside the group scheme.
    "CHE_QUAL23": ["CHE_QUAL19"],
    # These are all solubility-rule applications.
    "CHE_QUAL12": ["CHEM_SOLUTION7"],
    "CHE_QUAL17": ["CHEM_SOLUTION7"],
    "CHE_QUAL18": ["CHEM_SOLUTION7"],
    # Controlling sulfide concentration with a weak acid is Ksp plus partial
    # dissociation — the two ideas the explanation is made of.
    "CHE_QUAL4":  ["CHE_EQUILIBRIUM10", "CHE_EQUILIBRIUM15"],
    "CHE_QUAL7":  ["CHE_EQUILIBRIUM15"],
    # Distinguishing halides by silver-halide solubility in ammonia needs the
    # insoluble-chloride fact and ammine complexation.
    "CHE_QUAL9":  ["CHE_QUAL12", "CHE_COORD7"],
    # An ammine complex breaking down presupposes it forming.
    "CHE_QUAL10": ["CHE_QUAL20", "CHE_COORD7"],
    "CHE_QUAL20": ["CHE_COORD7"],
    # Nessler's: composition, then what it detects.
    "CHE_QUAL21": ["CHE_QUAL11"],
    "CHE_QUAL5":  ["CHE_QUAL21"],
    # Prussian blue as evidence presupposes the compound itself.
    "CHE_QUAL8":  ["CHE_COORD11"],

    # ---------------------------------------------------------------- Batch 3
    # CHEM_CAT — every named-process catalyst recall presupposes what a catalyst
    # does; the enzyme instances presuppose the enzyme definition.
    "CHEM_CAT1":  ["CHEM_CAT6"],
    "CHEM_CAT2":  ["CHEM_CAT6"],
    "CHEM_CAT3":  ["CHEM_CAT2"],
    "CHEM_CAT4":  ["CHEM_CAT2"],
    "CHEM_CAT5":  ["CHEM_CAT2"],
    "CHEM_CAT13": ["CHEM_CAT2"],
    "CHEM_CAT12": ["CHEM_CAT8"],
    "CHEM_CAT9":  ["CHEM_CAT8"],

    # CHE_COORD — recognising a complex comes first, then counting, then judging.
    "CHE_COORD3":  ["CHE_COORD7"],
    "CHE_COORD12": ["CHE_COORD3"],
    "CHE_COORD4":  ["CHE_COORD3", "CHE_COORD7"],
    "CHE_COORD9":  ["CHE_COORD4"],
    "CHE_COORD10": ["CHE_COORD3", "CHEM_REDOX20"],
    "CHE_COORD6":  ["CHE_COORD3", "CHE_BONDING37"],

    # CHEM_GAS / CHEM_GASLAW / CHEM_KINETICS (legacy-alias topics)
    "CHEM_GAS3":     ["CHE_GASLAWS34"],
    "CHEM_GAS4":     ["CHEM_GAS3"],
    "CHEM_GASLAW1":  ["CHE_GASLAWS26", "CHE_GASLAWS22"],
    "CHEM_GASLAW5":  ["CHE_GASLAWS34"],
    # Identifying a gas from its molar mass is a step inside the rms-velocity route.
    "CHE_GASLAWS10": ["CHEM_GASLAW3"],
    "CHEM_KINETICS1": ["CHEM_KIN20"],

    # CHEM_NOM — naming rules before named instances; the ore definition anchors
    # every mineral-formula recall in CHEM_DBLOCK below.
    "CHEM_NOM7":  ["CHEM_NOM3"],
    "CHEM_NOM5":  ["CHEM_NOM8"],
    "CHEM_NOM11": ["CHEM_NOM8"],
    "CHEM_NOM9":  ["CHEM_NOM8"],

    # CHEM_DBLOCK — the d-block classification anchors the element facts; the ore
    # definition anchors the mineral formulas; alloy compositions anchor the alloys.
    "CHEM_DBLOCK14": ["CHE_ATOMIC11"],
    "CHEM_DBLOCK5":  ["CHEM_DBLOCK14"],
    "CHEM_DBLOCK4":  ["CHEM_DBLOCK14"],
    "CHEM_DBLOCK6":  ["CHE_ATOMIC11"],
    "CHEM_DBLOCK8":  ["CHEM_DBLOCK14"],
    "CHEM_DBLOCK11": ["CHEM_NOM6"],
    "CHEM_DBLOCK7":  ["CHEM_NOM6"],
    "CHEM_DBLOCK9":  ["CHEM_NOM6"],
    "CHEM_DBLOCK17": ["CHEM_NOM6"],
    "CHEM_DBLOCK18": ["CHEM_NOM6"],
    "CHEM_DBLOCK12": ["CHEM_DESCRIPTIVE2"],
    "CHEM_DBLOCK16": ["CHEM_DESCRIPTIVE2"],
    "CHEM_DBLOCK19": ["CHEM_DESCRIPTIVE2"],
    "CHEM_DBLOCK15": ["CHEM_DESCRIPTIVE6"],

    # CHEM_ENV — acid rain, soil pH, pollution metrics and green chemistry each
    # form a small chain; the chemistry they rest on is in CHE_ACIDBASE and
    # CHE_ORGANIC.
    "CHEM_ENV20": ["CHE_ACIDBASE3"],
    "CHEM_ENV11": ["CHE_ACIDBASE50"],
    "CHEM_ENV21": ["CHEM_ENV20"],
    "CHEM_ENV4":  ["CHEM_ENV20"],
    "CHEM_ENV3":  ["CHEM_ENV20"],
    "CHEM_ENV13": ["CHEM_ENV20"],
    "CHEM_ENV19": ["CHEM_ENV13"],
    "CHEM_ENV5":  ["CHEM_NOM3"],
    "CHEM_ENV12": ["CHEM_DESCRIPTIVE1"],
    "CHEM_ENV26": ["CHE_ACIDBASE50"],
    "CHEM_ENV10": ["CHEM_ENV26"],
    "CHEM_ENV27": ["CHEM_ENV26"],
    "CHEM_ENV28": ["CHEM_ENV17"],
    "CHEM_ENV14": ["CHEM_ENV17"],
    "CHEM_ENV29": ["CHE_STOICHIOMETRY22"],
    "CHEM_ENV8":  ["CHEM_ENV7"],
    "CHEM_ENV25": ["CHE_ORGANIC139", "CHE_ORGANIC51"],

    # ---------------------------------------------------------------- Batch 4
    # CHEM_PERIODIC — the table's ordering principle anchors the layout facts;
    # the electron-affinity and ionization-energy definitions anchor the anomalies.
    "CHEM_PERIODIC25": ["CHEM_PERIODIC37"],
    "CHEM_PERIODIC18": ["CHEM_PERIODIC37"],
    "CHEM_PERIODIC26": ["CHEM_PERIODIC37"],
    "CHEM_PERIODIC19": ["CHEM_DBLOCK6"],
    "CHEM_PERIODIC39": ["CHE_ATOMIC46"],
    "CHEM_PERIODIC23": ["CHEM_PERIODIC27"],
    "CHEM_PERIODIC22": ["CHEM_PERIODIC27", "CHEM_PERIODIC23"],
    "CHEM_PERIODIC3":  ["CHEM_PERIODIC27"],
    "CHEM_PERIODIC40": ["CHE_ATOMIC54"],
    "CHEM_PERIODIC20": ["CHEM_PERIODIC40"],
    "CHEM_PERIODIC21": ["CHEM_PERIODIC40"],
    "CHEM_PERIODIC31": ["CHEM_PERIODIC6"],
    "CHEM_PERIODIC15": ["CHEM_PERIODIC6", "CHE_ATOMIC11"],
    "CHEM_PERIODIC14": ["CHEM_PERIODIC11"],
    "CHEM_PERIODIC16": ["CHEM_PERIODIC31"],
    "CHEM_PERIODIC41": ["CHEM_PERIODIC16"],
    "CHEM_PERIODIC17": ["CHEM_PERIODIC14"],
    "CHEM_PERIODIC24": ["CHEM_PERIODIC13"],
    "CHEM_PERIODIC35": ["CHEM_PERIODIC13"],
    "CHEM_PERIODIC32": ["CHE_ACIDBASE3"],
    "CHEM_PERIODIC33": ["CHEM_PERIODIC14"],

    # CHEM_SPEC — the wavelength ordering anchors the applications.
    "CHEM_SPEC4": ["CHE_ATOMIC25"],
    "CHEM_SPEC3": ["CHEM_SPEC4"],
    "CHEM_SPEC5": ["CHEM_SPEC4"],

    # CHE_ATOMIC — three chains: nuclear composition, quantum numbers/orbitals,
    # and the spectral/photon-energy relations.
    "CHE_ATOMIC34": ["CHE_ATOMIC33"],
    "CHE_ATOMIC30": ["CHE_ATOMIC33", "CHE_ATOMIC34"],
    "CHE_ATOMIC32": ["CHE_ATOMIC33"],
    "CHE_ATOMIC21": ["CHE_ATOMIC6"],
    "CHE_ATOMIC56": ["CHE_ATOMIC6"],
    "CHE_ATOMIC31": ["CHE_ATOMIC6"],
    "CHE_ATOMIC64": ["CHE_ATOMIC31"],
    "CHE_ATOMIC57": ["CHE_ATOMIC7"],
    "CHE_ATOMIC36": ["CHE_ATOMIC57"],
    "CHE_ATOMIC43": ["CHE_ATOMIC23"],
    "CHE_ATOMIC26": ["CHE_ATOMIC25"],
    "CHE_ATOMIC27": ["CHE_ATOMIC25"],
    "CHE_ATOMIC16": ["CHE_ATOMIC11"],
    "CHE_ATOMIC37": ["CHE_ATOMIC46"],
    "CHE_ATOMIC53": ["CHE_ATOMIC37"],
    "CHE_ATOMIC54": ["CHE_ATOMIC11"],
    "CHE_ATOMIC59": ["CHE_ATOMIC46"],
    "CHE_ATOMIC61": ["CHE_ATOMIC46"],
    # The named spectral series anchor identifying a particular line.
    "CHE_ATOMIC50": ["CHE_ATOMIC23"],

    # CHE_BONDING — hybridisation anchors geometry; the ionic/covalent trend
    # anchors the property comparisons.
    "CHE_BONDING10": ["CHE_BONDING8"],
    "CHE_BONDING33": ["CHE_BONDING10"],
    "CHE_BONDING15": ["CHE_BONDING10"],
    "CHE_BONDING35": ["CHE_ATOMIC11"],
    "CHE_BONDING29": ["CHE_ATOMIC37"],
    "CHE_BONDING17": ["CHE_BONDING29"],
    "CHE_BONDING16": ["CHE_BONDING37"],
    "CHE_BONDING26": ["CHEM_PERIODIC15"],
    "CHE_BONDING51": ["CHE_BONDING26"],
    "CHE_BONDING3":  ["CHE_BONDING56"],
    "CHE_BONDING34": ["CHEM_PERIODIC31"],
    "CHE_BONDING21": ["CHE_BONDING34"],
    "CHE_BONDING32": ["CHE_BONDING34"],
    "CHE_BONDING38": ["CHEM_PERIODIC15"],
    "CHE_BONDING48": ["CHE_BONDING43"],
    "CHE_BONDING53": ["CHE_BONDING43"],

    # ---------------------------------------------------------------- Batch 5
    # CHEM_REDOX — oxidation number and the reactivity series anchor everything;
    # the reagent-specific facts hang off the oxidising/reducing classification.
    "CHEM_REDOX36": ["CHEM_REDOX2"],
    "CHEM_REDOX11": ["CHEM_REDOX2"],
    "CHEM_REDOX12": ["CHEM_REDOX2"],
    "CHEM_REDOX13": ["CHEM_REDOX31"],
    "CHEM_REDOX26": ["CHEM_PERIODIC31"],
    "CHEM_REDOX10": ["CHEM_REDOX31", "CHEM_REDOX26"],
    "CHEM_REDOX9":  ["CHEM_REDOX36"],
    "CHEM_REDOX15": ["CHEM_REDOX36"],
    "CHEM_REDOX22": ["CHEM_REDOX15"],
    "CHEM_REDOX23": ["CHEM_REDOX35"],
    "CHEM_REDOX16": ["CHEM_REDOX36"],
    "CHEM_REDOX29": ["CHEM_REDOX16", "CHEM_REDOX34"],
    "CHEM_REDOX30": ["CHEM_REDOX31"],
    "CHEM_REDOX17": ["CHEM_REDOX30"],
    "CHEM_REDOX24": ["CHEM_REDOX36"],
    "CHEM_REDOX33": ["CHEM_REDOX36"],

    # CHEM_NUCLEAR — nuclear composition first, then reaction types.
    "CHEM_NUCLEAR2":  ["CHE_ATOMIC33"],
    "CHEM_NUCLEAR14": ["CHE_ATOMIC33"],
    "CHEM_NUCLEAR12": ["CHEM_NUCLEAR4"],
    "CHEM_NUCLEAR6":  ["CHEM_NUCLEAR2"],
    "CHEM_NUCLEAR5":  ["CHEM_NUCLEAR6"],
    "CHEM_NUCLEAR7":  ["CHEM_NUCLEAR6"],
    "CHEM_NUCLEAR13": ["CHEM_NUCLEAR1"],

    # CHE_BIOMOLECULE — the class definitions anchor the specific facts and tests.
    "CHE_BIOMOLECULE5":  ["CHE_BIOMOLECULE11"],
    "CHE_BIOMOLECULE21": ["CHE_BIOMOLECULE13"],
    "CHE_BIOMOLECULE14": ["CHE_BIOMOLECULE13"],
    "CHE_BIOMOLECULE18": ["CHE_BIOMOLECULE21"],
    "CHE_BIOMOLECULE10": ["CHE_BIOMOLECULE21"],
    "CHE_BIOMOLECULE6":  ["CHE_BIOMOLECULE20"],
    "CHE_BIOMOLECULE22": ["CHE_BIOMOLECULE17"],
    "CHE_BIOMOLECULE26": ["CHE_BIOMOLECULE17"],

    # CHEM_ANALYTICAL
    "CHEM_ANALYTICAL17": ["CHEM_ANALYTICAL4"],
    "CHEM_ANALYTICAL11": ["CHEM_REDOX36"],
    "CHEM_ANALYTICAL12": ["CHE_ACIDBASE50"],
    "CHEM_ANALYTICAL5":  ["CHEM_SOLUTION7"],

    # CHEM_SOLUTION
    "CHEM_SOLUTION11": ["CHEM_SOLUTION6"],
    "CHEM_SOLUTION12": ["CHEM_SOLUTION6"],
    "CHEM_SOLUTION13": ["CHEM_SOLUTION12"],
    "CHEM_SOLUTION14": ["CHEM_SOLUTION3"],
    "CHEM_SOLUTION5":  ["CHEM_SOLUTION7"],
    "CHEM_STEREO6":    ["CHEM_STEREO4"],

    # CHE_ACIDBASE — the Bronsted definition anchors the classification chain;
    # Kw anchors the pH facts; buffer pH anchors the buffer applications.
    "CHE_ACIDBASE62": ["CHE_ACIDBASE56"],
    "CHE_ACIDBASE60": ["CHE_ACIDBASE56"],
    "CHE_ACIDBASE58": ["CHE_ACIDBASE56"],
    "CHE_ACIDBASE40": ["CHE_ACIDBASE56"],
    "CHE_ACIDBASE10": ["CHE_ACIDBASE40"],
    "CHE_ACIDBASE46": ["CHEM_REDOX2"],
    "CHE_ACIDBASE47": ["CHEM_PERIODIC31"],
    "CHE_ACIDBASE8":  ["CHE_ACIDBASE3"],
    "CHE_ACIDBASE11": ["CHEM_NOM3"],
    "CHE_ACIDBASE9":  ["CHE_ACIDBASE11"],
    "CHE_ACIDBASE5":  ["CHE_ACIDBASE3"],
    "CHE_ACIDBASE12": ["CHE_ACIDBASE5"],
    "CHE_ACIDBASE21": ["CHE_ACIDBASE50"],
    "CHE_ACIDBASE24": ["CHE_ACIDBASE21"],
    "CHE_ACIDBASE22": ["CHE_ACIDBASE33"],
    "CHE_ACIDBASE25": ["CHE_ACIDBASE33"],
    "CHE_ACIDBASE14": ["CHE_ACIDBASE20"],
    "CHE_ACIDBASE42": ["CHE_ACIDBASE20"],

    # CHE_GASLAWS — units, then ideal/real behaviour, then kinetic-theory results.
    "CHE_GASLAWS28": ["CHE_GASLAWS40"],
    "CHE_GASLAWS35": ["CHE_GASLAWS26"],
    "CHE_GASLAWS36": ["CHE_GASLAWS26"],
    "CHE_GASLAWS37": ["CHE_GASLAWS22"],
    "CHE_GASLAWS33": ["CHE_GASLAWS34"],
    "CHE_GASLAWS7":  ["CHE_GASLAWS34"],
    "CHE_GASLAWS3":  ["CHEM_SOLUTION7"],
    "CHE_GASLAWS4":  ["CHE_GASLAWS3"],

    # CHE_THERMOCHEM — the enthalpy definition anchors the named enthalpy types.
    "CHE_THERMOCHEM20": ["CHE_THERMOCHEM26"],
    "CHE_THERMOCHEM11": ["CHE_THERMOCHEM26"],
    "CHE_THERMOCHEM23": ["CHE_THERMOCHEM11"],
    "CHE_THERMOCHEM5":  ["CHE_THERMOCHEM1"],

    # CHE_STOICHIOMETRY
    "CHE_STOICHIOMETRY19": ["CHE_STOICHIOMETRY20"],
    "CHE_STOICHIOMETRY5":  ["CHE_STOICHIOMETRY28"],
    "CHE_STOICHIOMETRY25": ["CHE_STOICHIOMETRY28"],
    "CHE_STOICHIOMETRY9":  ["CHE_STOICHIOMETRY17"],
    "CHE_STOICHIOMETRY29": ["CHE_STOICHIOMETRY17"],
    "CHE_STOICHIOMETRY30": ["CHE_STOICHIOMETRY26"],

    # CHEM_KIN
    "CHEM_KIN6":  ["CHEM_KIN2"],
    "CHEM_KIN1":  ["CHEM_KIN2"],
    "CHEM_KIN13": ["CHEM_KIN2"],

    # CHE_EQUILIBRIUM — the law of mass action anchors the constants.
    "CHE_EQUILIBRIUM36": ["CHE_EQUILIBRIUM30"],
    "CHE_EQUILIBRIUM18": ["CHE_EQUILIBRIUM30"],
    "CHE_EQUILIBRIUM39": ["CHE_EQUILIBRIUM31"],

    "CHE_ELECTROCHEM10": ["CHE_ELECTROCHEM9"],

    # ---------------------------------------------------------------- Batch 6
    # CHE_ORGANIC. Organised as chains rather than a hub: aromaticity, the
    # homologous-series basics, and then each functional-group family hanging off
    # the reaction that introduces it.

    # Aromaticity
    "CHE_ORGANIC7":   ["CHE_BONDING8"],
    "CHE_ORGANIC111": ["CHE_ORGANIC7"],
    "CHE_ORGANIC112": ["CHE_ORGANIC7"],
    "CHE_ORGANIC136": ["CHE_ORGANIC111"],
    "CHE_ORGANIC147": ["CHE_ORGANIC111"],
    "CHE_ORGANIC76":  ["CHE_ORGANIC111"],
    "CHE_ORGANIC148": ["CHE_ORGANIC76"],
    "CHE_ORGANIC94":  ["CHE_ORGANIC111"],
    "CHE_ORGANIC124": ["CHE_ORGANIC111"],
    "CHE_ORGANIC77":  ["CHE_ORGANIC111"],
    "CHE_ORGANIC121": ["CHE_ORGANIC111"],
    "CHE_ORGANIC41":  ["CHE_ORGANIC147"],
    "CHE_ORGANIC145": ["CHE_ORGANIC20"],

    # Homologous series, isomerism and reactive intermediates
    "CHE_ORGANIC99":  ["CHE_ORGANIC101"],
    "CHE_ORGANIC100": ["CHE_ORGANIC20"],
    "CHE_ORGANIC156": ["CHE_ORGANIC107"],
    "CHE_ORGANIC14":  ["CHE_ORGANIC107"],
    "CHE_ORGANIC6":   ["CHE_BONDING8"],
    "CHE_ORGANIC98":  ["CHE_ORGANIC101"],
    "CHE_ORGANIC93":  ["CHE_ORGANIC101"],
    "CHE_ORGANIC155": ["CHE_ORGANIC101"],

    # Alkanes, alkenes, alkynes
    "CHE_ORGANIC40":  ["CHE_ORGANIC156"],
    "CHE_ORGANIC85":  ["CHE_ORGANIC6"],
    "CHE_ORGANIC86":  ["CHE_ORGANIC85"],
    "CHE_ORGANIC78":  ["CHE_ORGANIC101"],
    "CHE_ORGANIC123": ["CHE_ORGANIC78"],
    "CHE_ORGANIC73":  ["CHE_ORGANIC101"],
    "CHE_ORGANIC84":  ["CHE_ORGANIC6"],

    # Carbonyls and carboxylic-acid derivatives
    "CHE_ORGANIC102": ["CHE_ORGANIC49"],
    "CHE_ORGANIC118": ["CHE_ORGANIC49"],
    "CHE_ORGANIC119": ["CHE_ORGANIC49"],
    "CHE_ORGANIC4":   ["CHE_ORGANIC119"],
    "CHE_ORGANIC27":  ["CHE_ORGANIC4"],
    "CHE_ORGANIC19":  ["CHE_ORGANIC49"],
    "CHE_ORGANIC43":  ["CHE_ORGANIC150"],
    "CHE_ORGANIC113": ["CHE_ORGANIC150"],
    "CHE_ORGANIC48":  ["CHE_ORGANIC47"],
    "CHE_ORGANIC67":  ["CHE_ORGANIC47"],
    "CHE_ORGANIC18":  ["CHE_BIOMOLECULE27"],
    "CHE_ORGANIC103": ["CHE_ORGANIC127"],

    # Phenol and aniline
    "CHE_ORGANIC70":  ["CHE_ORGANIC111"],
    "CHE_ORGANIC130": ["CHE_ORGANIC70"],
    "CHE_ORGANIC23":  ["CHE_ORGANIC70"],
    "CHE_ORGANIC79":  ["CHE_ORGANIC70"],
    "CHE_ORGANIC129": ["CHE_ORGANIC111"],
    "CHE_ORGANIC126": ["CHE_ORGANIC129"],
    "CHE_ORGANIC91":  ["CHE_ORGANIC76"],
    "CHE_ORGANIC90":  ["CHE_ORGANIC91"],
    "CHE_ORGANIC31":  ["CHE_ORGANIC91"],
    "CHE_ORGANIC32":  ["CHE_ORGANIC31"],
    "CHE_ORGANIC88":  ["CHE_ORGANIC89"],
    "CHE_ORGANIC26":  ["CHE_ORGANIC89"],
    "CHE_ORGANIC92":  ["CHE_ORGANIC41"],

    # Halogen derivatives and chloroform
    "CHE_ORGANIC80":  ["CHE_ORGANIC113"],
    "CHE_ORGANIC135": ["CHE_ORGANIC80"],
    "CHE_ORGANIC134": ["CHE_ORGANIC135"],
    "CHE_ORGANIC82":  ["CHE_ORGANIC135"],
    "CHE_ORGANIC68":  ["CHE_ORGANIC40"],
    "CHE_ORGANIC69":  ["CHE_ORGANIC68"],
    "CHE_ORGANIC143": ["CHE_ORGANIC68"],

    # Alcohols, ethers, esters, glycerol
    "CHE_ORGANIC36":  ["CHE_ORGANIC37"],
    "CHE_ORGANIC64":  ["CHE_ORGANIC62"],
    "CHE_ORGANIC59":  ["CHE_ORGANIC58"],
    "CHE_ORGANIC97":  ["CHE_ORGANIC59"],
    "CHE_ORGANIC10":  ["CHE_ORGANIC11"],
    # Methanol comes from water gas — the CHEM_DESCRIPTIVE fact it rests on.
    "CHE_ORGANIC60":  ["CHEM_DESCRIPTIVE9"],
    "CHE_ORGANIC61":  ["CHE_ORGANIC60"],
    "CHE_ORGANIC140": ["CHE_ORGANIC60"],
    "CHE_ORGANIC138": ["CHE_ORGANIC50"],
    "CHE_ORGANIC83":  ["CHE_ORGANIC138"],

    # Polymers, fuels and industrial materials
    "CHE_ORGANIC131": ["CHE_ORGANIC55"],
    "CHE_ORGANIC57":  ["CHE_ORGANIC55"],
    "CHE_ORGANIC132": ["CHE_ORGANIC99"],
    "CHE_ORGANIC52":  ["CHE_ORGANIC132"],
    "CHE_ORGANIC133": ["CHE_ORGANIC52"],
    "CHE_ORGANIC141": ["CHE_ORGANIC142"],
}


def would_cycle(existing: dict, new_edges: dict[str, list[str]]) -> list[tuple[str, str]]:
    """Return any (prereq, dependent) pairs that would close a cycle."""
    adj: dict[str, set[str]] = defaultdict(set)   # prereq -> dependents
    for dep, ancestors in existing.items():
        for a in ancestors or []:
            adj[a["id"]].add(dep)
    for dep, prereqs in new_edges.items():
        for p in prereqs:
            adj[p].add(dep)

    bad = []
    for dep, prereqs in new_edges.items():
        for p in prereqs:
            # can we already get from dep back to p?
            seen, q = set(), deque([dep])
            while q:
                cur = q.popleft()
                if cur == p:
                    bad.append((p, dep))
                    break
                for nxt in adj.get(cur, ()):
                    if nxt not in seen:
                        seen.add(nxt)
                        q.append(nxt)
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    tuples = json.loads((HERE / "tuples.json").read_text(encoding="utf-8"))
    prereqs = json.loads((HERE / "prereqs.json").read_text(encoding="utf-8"))
    desc = {t["skillId"]: t["skillFull"] for t in tuples}

    referenced = set(EDGES) | {p for v in EDGES.values() for p in v}
    unknown = sorted(referenced - set(desc))
    if unknown:
        sys.exit(f"error: unknown skillIds: {unknown}")

    # A repeated key in the EDGES literal is silently shadowed by Python, which
    # would drop an earlier batch's edges from the table without any error. The
    # source is the record of what was decided, so guard it.
    src = Path(__file__).read_text(encoding="utf-8")
    table = src.split("EDGES: dict[str, list[str]] = {", 1)[1].split("\n}", 1)[0]
    keys = re.findall(r'^\s*"([A-Z0-9_]+)"\s*:', table, re.M)
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        sys.exit(f"error: duplicate keys in EDGES (later ones shadow earlier): {dupes}")

    self_edges = sorted(d for d, ps in EDGES.items() if d in ps)
    if self_edges:
        sys.exit(f"error: skill listed as its own prerequisite: {self_edges}")

    cycles = would_cycle(prereqs, EDGES)
    if cycles:
        sys.exit(f"error: these edges would create a cycle: {cycles}")

    added = skipped = 0
    for dep, prereq_ids in sorted(EDGES.items()):
        entry = prereqs.setdefault(dep, [])
        have = {a["id"] for a in entry}
        for pid in prereq_ids:
            if pid in have:
                skipped += 1
                continue
            entry.append({"id": pid, "full": desc[pid], "depth": 0})
            added += 1
            print(f"  + {dep:22} <- {pid:22} {desc[pid][:52]}")

    print(f"\nedges added: {added}   already present: {skipped}")
    print(f"skills given at least one prerequisite: {len(EDGES)}")

    if args.apply:
        (HERE / "prereqs.json").write_text(
            json.dumps(prereqs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written to prereqs.json")
    else:
        print("(dry run; nothing written)")


if __name__ == "__main__":
    main()
