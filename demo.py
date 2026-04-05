"""
demo.py
-------
End-to-end demonstration of the adaptive tutor system.

Skill tree constructed:
    arithmetic (root)
      └── algebra_basics (root)
            ├── linear_equations  (derived from arithmetic + algebra_basics)
            │     └── quadratic_equations (derived from linear_equations)
            └── inequalities (derived from algebra_basics)

Simulates a student answering 8 questions of varying Bloom levels and
prints the evolving knowledge state after each answer.
"""

from __future__ import annotations

import json
from typing import List, Tuple

from bloom_taxonomy import BloomLevel
from bkt import BKTParams
from mastery_updater import MasteryUpdater
from question import Question
from skill import Skill
from skill_tree import SkillTree
from student_model import StudentModel


# ============================================================= build skill tree
def build_sample_skill_tree() -> SkillTree:
    tree = SkillTree()

    # Root / prerequisite skills
    arithmetic = Skill(
        skill_id    = "arithmetic",
        name        = "Arithmetic",
        description = "Basic operations: +, −, ×, ÷",
        topics      = ["mathematics", "arithmetic"],
    )
    algebra_basics = Skill(
        skill_id    = "algebra_basics",
        name        = "Algebra Basics",
        description = "Variables, expressions, simple substitution",
        topics      = ["mathematics", "algebra"],
    )

    # Derived skills
    linear_equations = Skill(
        skill_id    = "linear_equations",
        name        = "Linear Equations",
        description = "Solving equations of the form ax + b = c",
        topics      = ["algebra", "equations"],
    )
    quadratic_equations = Skill(
        skill_id    = "quadratic_equations",
        name        = "Quadratic Equations",
        description = "Solving ax² + bx + c = 0 by factoring, completing the square, or quadratic formula",
        topics      = ["algebra", "equations"],
    )
    inequalities = Skill(
        skill_id    = "inequalities",
        name        = "Inequalities",
        description = "Solving and graphing linear inequalities",
        topics      = ["algebra", "inequalities"],
    )

    # Register skills
    for skill in [arithmetic, algebra_basics, linear_equations, quadratic_equations, inequalities]:
        tree.add_skill(skill)

    # Define prerequisite edges  (parent → child)
    tree.add_prerequisite("linear_equations",    "arithmetic")
    tree.add_prerequisite("linear_equations",    "algebra_basics")
    tree.add_prerequisite("quadratic_equations", "linear_equations")
    tree.add_prerequisite("inequalities",        "algebra_basics")

    return tree


# ============================================================= build questions
def build_sample_questions() -> List[Question]:
    return [
        # Q1 — arithmetic, REMEMBER (should raise mastery of arithmetic at low bloom)
        Question(
            question_id   = "q1",
            text          = "What is 7 × 8?",
            options       = ["54", "56", "64", "48"],
            correct_index = 1,
            topic         = "arithmetic",
            bloom_level   = BloomLevel.REMEMBER,
            skill_ids     = ["arithmetic"],
        ),
        # Q2 — algebra_basics, UNDERSTAND
        Question(
            question_id   = "q2",
            text          = "If x = 3, what is the value of 2x + 5?",
            options       = ["8", "10", "11", "13"],
            correct_index = 2,
            topic         = "algebra",
            bloom_level   = BloomLevel.UNDERSTAND,
            skill_ids     = ["algebra_basics"],
        ),
        # Q3 — linear_equations, APPLY
        Question(
            question_id   = "q3",
            text          = "Solve for x: 3x − 9 = 0",
            options       = ["x = 0", "x = 3", "x = −3", "x = 9"],
            correct_index = 1,
            topic         = "algebra",
            bloom_level   = BloomLevel.APPLY,
            skill_ids     = ["linear_equations", "arithmetic"],
        ),
        # Q4 — wrong answer on arithmetic (REMEMBER) — mastery should dip slightly
        Question(
            question_id   = "q4",
            text          = "What is 13 − 7?",
            options       = ["5", "7", "6", "8"],
            correct_index = 2,
            topic         = "arithmetic",
            bloom_level   = BloomLevel.REMEMBER,
            skill_ids     = ["arithmetic"],
        ),
        # Q5 — linear_equations, ANALYZE (higher bloom → larger delta)
        Question(
            question_id   = "q5",
            text          = "Which of the following systems has no solution?",
            options       = [
                "y = 2x + 1  and  y = 2x − 3",
                "y = x       and  y = −x",
                "y = 3x      and  y = x + 2",
                "y = x + 1   and  y = 2x + 1",
            ],
            correct_index = 0,
            topic         = "algebra",
            bloom_level   = BloomLevel.ANALYZE,
            skill_ids     = ["linear_equations"],
        ),
        # Q6 — inequalities, APPLY (correct)
        Question(
            question_id   = "q6",
            text          = "Solve: 2x + 4 > 10",
            options       = ["x > 3", "x > 4", "x < 3", "x < 7"],
            correct_index = 0,
            topic         = "inequalities",
            bloom_level   = BloomLevel.APPLY,
            skill_ids     = ["inequalities"],
        ),
        # Q7 — quadratic_equations, APPLY
        Question(
            question_id   = "q7",
            text          = "Solve: x² − 5x + 6 = 0",
            options       = ["x = 2, 3", "x = −2, −3", "x = 1, 6", "x = −1, 6"],
            correct_index = 0,
            topic         = "algebra",
            bloom_level   = BloomLevel.APPLY,
            skill_ids     = ["quadratic_equations", "linear_equations"],
        ),
        # Q8 — linear_equations, CREATE (highest bloom — largest potential delta)
        Question(
            question_id   = "q8",
            text          = "A student earns $12/h. Write and solve an equation to find how many "
                            "hours she must work to earn $300 after a $24 deduction.",
            options       = ["27 hours", "26 hours", "25 hours", "23 hours"],
            correct_index = 0,
            topic         = "algebra",
            bloom_level   = BloomLevel.CREATE,
            skill_ids     = ["linear_equations"],
        ),
    ]


# ============================================================= simulation helpers
SEPARATOR = "─" * 70

def print_state(student: StudentModel, label: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {label}")
    print(f"{'═' * 70}")
    summary = student.summary()
    if not summary:
        print("  (no skills encountered yet)")
        return
    header = f"  {'Skill':<25} {'Mastery':>8} {'P(learned)':>10} {'Bloom Level':<14} {'Accuracy':>8}"
    print(header)
    print(f"  {'-'*63}")
    for sid, info in summary.items():
        print(
            f"  {sid:<25} {info['mastery']:>7.1f}%"
            f"  {info['p_learned']:>9.4f}"
            f"  {info['bloom_level']:<14}"
            f"  {info['accuracy']*100:>7.1f}%"
        )


def simulate_answer(
    student: StudentModel,
    updater: MasteryUpdater,
    question: Question,
    student_choice: int,
) -> None:
    is_correct = question.is_correct(student_choice)
    result_str = "✓ CORRECT" if is_correct else "✗ WRONG"
    print(f"\n{SEPARATOR}")
    print(f"  [{question.question_id.upper()}]  {question.text}")
    print(f"  Bloom: {question.bloom_level.name:<12}  Skills: {question.skill_ids}")
    print(f"  Student chose: '{question.options[student_choice]}'  →  {result_str}")
    updater.process_answer(student, question, is_correct)


# ============================================================= main
def main() -> None:
    print("\n" + "═" * 70)
    print("  ADAPTIVE TUTOR — DEMO SESSION")
    print("═" * 70)

    # ---- build shared infrastructure ----
    skill_tree = build_sample_skill_tree()

    print(f"\n  Skill tree built: {skill_tree}")
    print("  Topological order:")
    for skill in skill_tree.topological_order():
        ptype = "(root)" if skill.is_prerequisite else f"(requires: {skill.parent_ids})"
        print(f"    • {skill.skill_id:<25} {ptype}")

    # ---- configure student ----
    student = StudentModel(
        student_id="alice",
        default_bkt_params=BKTParams.default(),
    )
    # Use a faster learning rate for the root arithmetic skill
    student.set_bkt_params("arithmetic", BKTParams.fast_learner())

    updater = MasteryUpdater(
        skill_tree             = skill_tree,
        base_mastery_scale     = 20.0,
        propagate_to_ancestors = True,
        ancestor_decay         = 0.40,
    )

    print_state(student, "INITIAL STATE (before any questions)")

    # ---- simulate answers ----
    # (question, student_choice_index)
    session: List[Tuple[Question, int]] = [
        (build_sample_questions()[0], 1),   # Q1 arithmetic  REMEMBER  ✓
        (build_sample_questions()[1], 2),   # Q2 algebra      UNDERSTAND ✓
        (build_sample_questions()[2], 1),   # Q3 linear eq    APPLY      ✓
        (build_sample_questions()[3], 0),   # Q4 arithmetic   REMEMBER   ✗ (wrong: "5", correct is "6")
        (build_sample_questions()[4], 0),   # Q5 linear eq    ANALYZE    ✓
        (build_sample_questions()[5], 0),   # Q6 inequalities APPLY      ✓
        (build_sample_questions()[6], 0),   # Q7 quadratic    APPLY      ✓
        (build_sample_questions()[7], 0),   # Q8 linear eq    CREATE     ✓
    ]

    for question, choice in session:
        simulate_answer(student, updater, question, choice)
        print_state(student, f"STATE AFTER {question.question_id.upper()}")

    # ---- final accessibility check ----
    print(f"\n{'═' * 70}")
    print("  SKILL ACCESSIBILITY (threshold: 50% mastery on all prerequisites)")
    print("═" * 70)
    for skill in skill_tree.topological_order():
        accessible = student.is_skill_accessible(skill.skill_id, skill_tree, mastery_threshold=50.0)
        icon = "✓" if accessible else "✗"
        print(f"  {icon} {skill.skill_id}")

    print(f"\n{'═' * 70}\n")


if __name__ == "__main__":
    main()
