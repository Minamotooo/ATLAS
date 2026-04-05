"""
diagnostic_demo.py
------------------
Demonstrates DiagnosticSession with the db_fetch / db_update calling
convention that matches the updated MasteryUpdater.

An in-memory dict simulates the database so the demo is self-contained.
In production, replace db_fetch / db_update with your real DB layer.
"""

from __future__ import annotations

from bloom_taxonomy import BloomLevel, get_level_from_mastery
from diagnostic import DiagnosticSession
from skill import Skill
from skill_tree import SkillTree


# ============================================================= in-memory DB
# Simulates the persistence layer.
# Schema: {(userid, skill_id): {'mastery': float, 'p_learned': float, 'p_transition': float}}
_db: dict = {}

def db_fetch(userid: str, skill_id: str) -> dict:
    key = (userid, skill_id)
    if key not in _db:
        _db[key] = {'mastery': 0.0, 'p_learned': 0.0, 'p_transition': 0.01}
    return _db[key]

def db_update(
    userid: str,
    skill_id: str,
    mastery: float,
    p_learned: float,
    p_transition: float | None = None,
) -> None:
    previous = _db.get((userid, skill_id), {'p_transition': 0.01})
    _db[(userid, skill_id)] = {
        'mastery': mastery,
        'p_learned': p_learned,
        'p_transition': previous['p_transition'] if p_transition is None else p_transition,
    }

def db_reset():
    """Clear all state between student simulations."""
    _db.clear()


# ============================================================= skill tree
def build_skill_tree() -> SkillTree:
    tree = SkillTree()
    skills = [
        Skill("arithmetic",       "Arithmetic",          "Basic operations",            ["mathematics", "arithmetic"]),
        Skill("algebra_basics",   "Algebra Basics",      "Variables and expressions",   ["mathematics", "algebra"]),
        Skill("linear_equations", "Linear Equations",    "Solving ax + b = c",          ["algebra", "equations"]),
        Skill("quadratic_eq",     "Quadratic Equations", "Solving ax² + bx + c = 0",   ["algebra", "equations"]),
        Skill("inequalities",     "Inequalities",        "Solving linear inequalities", ["algebra", "inequalities"]),
    ]
    for s in skills:
        tree.add_skill(s)

    tree.add_prerequisite("linear_equations", "arithmetic")
    tree.add_prerequisite("linear_equations", "algebra_basics")
    tree.add_prerequisite("quadratic_eq",     "linear_equations")
    tree.add_prerequisite("inequalities",     "algebra_basics")
    return tree


# ============================================================= simulation
def simulate(userid: str, skill_tree: SkillTree, answer_map: dict[str, bool]) -> None:
    SEP  = "─" * 68
    DSEP = "═" * 68

    db_reset()

    print(f"\n{DSEP}")
    print(f"  DIAGNOSTIC SESSION  —  student: {userid!r}")
    print(DSEP)

    session = DiagnosticSession(skill_tree, userid, db_fetch, db_update)

    print(f"\n  {'Skill':<25} {'Bloom tested':<16} {'Correct?':<12} {'p_learned':>10}  {'Mastery':>8}  {'P(T)':>7}")
    print(f"  {SEP}")

    q_count = 0
    while not session.is_complete():
        spec = session.next_question_spec()
        if spec is None:
            break

        is_correct = answer_map.get(spec.skill_id, True)
        session.record_answer(spec.skill_id, spec.bloom_level, is_correct)
        q_count += 1

        state  = db_fetch(userid, spec.skill_id)
        result = "✓ correct" if is_correct else "✗ incorrect"
        print(
            f"  {spec.skill_id:<25} {spec.bloom_level.name:<16}"
            f" {result:<12}  {state['p_learned']:>9.4f}   {state['mastery']:>6.1f}%  {state['p_transition']:>6.3f}"
        )

    # ---- final profile ---------------------------------------------------
    tested_n, total_n = session.progress()
    print(f"\n  Questions asked : {q_count}")
    print(f"  Directly tested : {tested_n} / {total_n} skills")
    print(f"  Inferred        : {total_n - tested_n} skills")

    print(f"\n  {SEP}")
    print(f"  {'Skill':<25} {'p_learned':>10}  {'Mastery':>8}  {'P(T)':>7}  {'Bloom Level':<14}  {'Source'}")
    print(f"  {SEP}")

    snapshot = session.mastery_snapshot()
    for skill in skill_tree.topological_order():
        sid     = skill.skill_id
        state   = db_fetch(userid, sid)
        mastery = state['mastery']
        p       = state['p_learned']
        p_t     = state['p_transition']
        bloom   = get_level_from_mastery(mastery).name
        source  = "tested" if session.tested[sid] else "inferred"
        print(f"  {sid:<25} {p:>10.4f}   {mastery:>6.1f}%  {p_t:>6.3f}  {bloom:<14}  {source}")

    print(f"\n{DSEP}\n")


# ============================================================= main
def main() -> None:
    skill_tree = build_skill_tree()

    print("\n" + "═" * 68)
    print("  SKILL TREE")
    print("═" * 68)
    for skill in skill_tree.topological_order():
        prereqs = f"requires: {skill.parent_ids}" if skill.parent_ids else "root"
        print(f"  • {skill.skill_id:<25} ({prereqs})")

    # Strong student — passes everything
    simulate("alice", skill_tree, {sid: True for sid in [
        "arithmetic", "algebra_basics", "linear_equations",
        "quadratic_eq", "inequalities",
    ]})

    # Struggling student — passes roots, fails derived skills
    simulate("bob", skill_tree, {
        "arithmetic":       True,
        "algebra_basics":   True,
        "linear_equations": False,
        "quadratic_eq":     False,
        "inequalities":     False,
    })

    # Mixed — strong everywhere except quadratics
    simulate("carol", skill_tree, {
        "arithmetic":       True,
        "algebra_basics":   True,
        "linear_equations": True,
        "quadratic_eq":     False,
        "inequalities":     True,
    })


if __name__ == "__main__":
    main()