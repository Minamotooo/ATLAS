"""
mastery_updater.py
------------------
The central update algorithm for the adaptive tutor.

Algorithm overview (per answered question)
==========================================

For each skill tagged in the question:

  1. BKT UPDATE
     Run the Bayesian Knowledge Tracing model to get an updated P(Lₙ₊₁).
     The *signed BKT delta* (Δp = P(Lₙ₊₁) − P(Lₙ)) is the raw learning signal.

         Δp > 0  when the observation increases our confidence the skill is known.
         Δp < 0  when the observation decreases it.

  2. BLOOM-WEIGHTED MASTERY DELTA
     The mastery change is proportional to three factors:

         Δmastery = Δp × bloom_weight(question.bloom_level)
                       × BASE_MASTERY_SCALE
                       × diminishing_returns_factor(current_mastery, bloom_ceiling)

     bloom_weight       — higher cognitive levels (Analyze, Create) produce
                          larger deltas, rewarding deeper thinking.
     BASE_MASTERY_SCALE — tunable constant (~20) that converts probability deltas
                          to mastery-point deltas.
     diminishing_returns— on a correct answer the gain is attenuated as mastery
                          approaches the bloom ceiling, so progress naturally slows
                          near the top of each band.

  3. MASTERY CAPPING
     • Correct answer: mastery is hard-capped at the question's Bloom band ceiling.
       The student cannot jump past a band without being assessed at the higher level.
     • Incorrect answer: no cap applied; mastery can fall below the current band floor.

  4. ANCESTOR PROPAGATION
     After updating the direct skill(s), the mastery delta is propagated upward
     through the skill DAG.  Each hop applies an exponential decay:

         Δmastery_ancestor = Δmastery_direct × decay^hop_distance

     BFS is used to avoid double-counting in diamond-shaped dependency graphs.
     For ancestors we propagate the raw mastery delta (no bloom ceiling cap),
     since the parent skill is not directly being assessed.

Design notes
============
• This class holds *no student state* — it reads from and writes to StudentModel.
• The BKT model used is injected at construction (open/closed principle).
• All tuneable constants are exposed as constructor parameters.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional

from bloom_taxonomy import BLOOM_WEIGHT, get_band
from bkt import BKTModel, BKTParams
from question import Question
from skill_tree import SkillTree
from student_model import StudentModel


class MasteryUpdater:
    """
    Updates a StudentModel after a student answers a question.

    Parameters
    ----------
    skill_tree              : The shared SkillTree for the session.
    base_mastery_scale      : Scales BKT probability deltas to mastery points.
                              Higher → more volatile mastery scores.
    propagate_to_ancestors  : Whether to push a decayed delta up the skill DAG.
    ancestor_decay          : Fraction of mastery delta passed to each ancestor level.
                              E.g. 0.4 means grandparent gets 0.4² × delta.
    """

    DEFAULT_BASE_SCALE:   float = 20.0
    DEFAULT_ANCESTOR_DECAY: float = 0.40

    def __init__(
        self,
        skill_tree: SkillTree,
        base_mastery_scale:     float = DEFAULT_BASE_SCALE,
        propagate_to_ancestors: bool  = True,
        ancestor_decay:         float = DEFAULT_ANCESTOR_DECAY,
    ) -> None:
        if not 0.0 <= ancestor_decay <= 1.0:
            raise ValueError("ancestor_decay must be in [0, 1].")
        self.skill_tree             = skill_tree
        self.base_mastery_scale     = base_mastery_scale
        self.propagate_to_ancestors = propagate_to_ancestors
        self.ancestor_decay         = ancestor_decay

    # ================================================================== public
    def process_answer(
        self,
        student: StudentModel,
        question: Question,
        is_correct: bool,
    ) -> None:
        """
        Process the student's answer and update all relevant skill states.

        Parameters
        ----------
        student     : The student whose model is being updated.
        question    : The question that was answered.
        is_correct  : Whether the student answered correctly.
        """
        bloom_band   = get_band(question.bloom_level)
        bloom_weight = BLOOM_WEIGHT[question.bloom_level]

        for skill_id in question.skill_ids:
            if skill_id not in self.skill_tree:
                # Gracefully skip unknown skills rather than raising.
                continue

            state       = student.get_skill_state(skill_id)
            bkt_params  = student.get_bkt_params(skill_id)
            bkt_model   = BKTModel(bkt_params)

            old_p    = state.p_learned
            old_mast = state.mastery

            # ---------------------------------------------------------- 1. BKT
            new_p   = bkt_model.update(old_p, is_correct)
            delta_p = new_p - old_p      # signed; positive → learned, negative → unlearned

            # ------------------------------------------- 2. Mastery delta
            mastery_delta = self._compute_mastery_delta(
                delta_p      = delta_p,
                bloom_weight = bloom_weight,
                current_mastery = old_mast,
                bloom_ceiling   = bloom_band.upper,
                is_correct   = is_correct,
            )

            # ------------------------------------------- 3. Cap & apply
            new_mast = old_mast + mastery_delta
            if is_correct:
                # Can't exceed the question's Bloom band ceiling.
                new_mast = min(new_mast, bloom_band.upper)
                # Don't accidentally decrease mastery on a correct answer
                # (can happen when the bloom band is below current mastery).
                new_mast = max(new_mast, old_mast)
            else:
                # No floor on incorrect — mastery can drop, but not below zero.
                new_mast = max(new_mast, 0.0)

            student.update_skill_state(skill_id, new_mast, new_p, is_correct)

            # ------------------------------------------- 4. Ancestors
            if self.propagate_to_ancestors:
                self._propagate_to_ancestors(
                    student    = student,
                    skill_id   = skill_id,
                    delta_mast = mastery_delta,
                    delta_p    = delta_p,
                    is_correct = is_correct,
                )

    # ================================================================== private: delta
    def _compute_mastery_delta(
        self,
        delta_p:         float,
        bloom_weight:    float,
        current_mastery: float,
        bloom_ceiling:   float,
        is_correct:      bool,
    ) -> float:
        """
        Compute the raw mastery delta before capping.

        Incorporates:
          • Bloom weight (higher cognitive levels → bigger delta)
          • Diminishing returns on correct answers as mastery approaches ceiling
          • A symmetric penalty on incorrect answers (no diminishing returns)
        """
        raw_delta = delta_p * bloom_weight * self.base_mastery_scale

        if is_correct and raw_delta > 0:
            # Diminishing-returns factor: gain → 0 as mastery → bloom_ceiling.
            # Uses a linear attenuation: (ceiling - current) / ceiling_width
            # so that the last few points before the ceiling are earned slowly.
            headroom = max(0.0, bloom_ceiling - current_mastery)
            attenuation = headroom / max(bloom_ceiling, 1.0)
            return raw_delta * attenuation
        else:
            # Wrong answer or unexpected negative delta: apply full magnitude.
            return raw_delta

    # ================================================================== private: propagation
    def _propagate_to_ancestors(
        self,
        student:    StudentModel,
        skill_id:   str,
        delta_mast: float,
        delta_p:    float,
        is_correct: bool,
    ) -> None:
        """
        Propagate mastery and BKT deltas to all ancestor skills via BFS,
        applying exponential decay at each hop.

        BFS guarantees each ancestor is visited at most once, so diamond
        shapes in the DAG are handled correctly (no double-counting).

        We propagate a *decayed* version of the direct skill's delta
        because parents are not directly being assessed — we infer a weak
        signal that the prerequisite is likely solid (or shaky).
        """
        visited: set[str] = set()

        # Queue entries: (skill_id_to_update, decay_factor_at_this_hop)
        queue: deque[tuple[str, float]] = deque()

        skill = self.skill_tree.get_skill(skill_id)
        for parent_id in skill.parent_ids:
            queue.append((parent_id, self.ancestor_decay))

        while queue:
            pid, decay = queue.popleft()
            if pid in visited:
                continue
            visited.add(pid)

            parent_state = student.get_skill_state(pid)
            old_p_anc    = parent_state.p_learned
            old_mast_anc = parent_state.mastery

            # Decayed deltas
            anc_delta_mast = delta_mast * decay
            anc_delta_p    = delta_p    * decay

            new_mast_anc = max(0.0, min(100.0, old_mast_anc + anc_delta_mast))
            new_p_anc    = max(0.0, min(1.0,   old_p_anc    + anc_delta_p))

            student.update_skill_state(pid, new_mast_anc, new_p_anc, is_correct)

            # Continue BFS upward with compounded decay
            parent_skill = self.skill_tree.get_skill(pid)
            for grandparent_id in parent_skill.parent_ids:
                if grandparent_id not in visited:
                    queue.append((grandparent_id, decay * self.ancestor_decay))

    # ================================================================== dunder
    def __repr__(self) -> str:
        return (
            f"MasteryUpdater("
            f"scale={self.base_mastery_scale}, "
            f"propagate={self.propagate_to_ancestors}, "
            f"decay={self.ancestor_decay})"
        )
