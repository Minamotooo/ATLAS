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

from collections import deque

from bkt import BKTModel, BKTParams
from skill_tree import SkillTree
from bloom_taxonomy import get_level_from_mastery

from enum import Enum, auto
class UpdateMode(Enum):
    DIAGNOSE = auto()
    REGULAR = auto()

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

    DEFAULT_ANCESTOR_DECAY: float = 0.40
    DEFAULT_SUCCESSOR_DECAY: float = 0.20
    DEFAULT_DECAY_THRESHOLD: float = 0.01

    def __init__(
        self,
        skill_tree: SkillTree,
        ancestor_decay:         float = DEFAULT_ANCESTOR_DECAY,
        successor_decay:        float = DEFAULT_SUCCESSOR_DECAY,
        threshold:              float = DEFAULT_DECAY_THRESHOLD,
    ) -> None:
        if not 0.0 <= ancestor_decay <= 1.0:
            raise ValueError("ancestor_decay must be in [0, 1].")
        if not 0.0 <= successor_decay <= 1.0:
            raise ValueError("successor_decay must be in [0, 1].")
        self.skill_tree             = skill_tree
        self.ancestor_decay         = ancestor_decay
        self.successor_decay        = successor_decay
        self.threshold              = threshold

    # ================================================================== public
    def update_skills(
        self,
        userid: str,
        skills: list,
        bloom_levels: list,
        mode: UpdateMode,
        is_correct: bool,
        db_fetch,
        db_update,
    ):
        """
        Update the student's mastery and BKT state for a set of skills.

        Parameters
        ----------
        userid        : The user ID (for DB context).
        skills        : List of skill IDs.
        bloom_levels  : List of BloomLevel (one per skill).
        bkt_params    : BKTParams object (shared for all skills).
        is_correct    : Whether the MCQ was answered correctly.
        db_fetch      : Function to fetch current state for a skill_id (returns dict with 'mastery', 'p_learned').
        db_update     : Function to update state for a skill_id (mastery, p_learned).

        Returns
        -------
        List of dicts: [{ 'skill_id': ..., 'mastery': ..., 'p_learned': ... }, ...]
        """
        updated = []
        # Select BKTParams based on mode
        if mode == UpdateMode.DIAGNOSE:
            bkt_params = BKTParams.fast_learner()
        else:
            bkt_params = BKTParams.default()

        for skill_id, bloom_level in zip(skills, bloom_levels):
            state = db_fetch(userid, skill_id)
            old_p = state['p_learned']

            bkt_model = BKTModel(bkt_params)
            raw_new_p = bkt_model.update(old_p, is_correct)
            # Compute current mastery band using p_learned
            current_band = get_level_from_mastery(old_p * 100.0)
            band_diff = bloom_level.value - current_band.value

            # Transform the new probability based on band_diff
            scale = self._bloom_band_scaling(band_diff, is_correct)
            new_p = old_p + (raw_new_p - old_p) * scale
            new_p = max(0.0, min(1.0, new_p))
            new_mast = new_p * 100.0

            db_update(userid, skill_id, new_mast, new_p)
            updated.append({'skill_id': skill_id, 'mastery': new_mast})

            self._propagate_to_ancestors(
                userid=userid,
                skill_id=skill_id,
                delta_p=new_p - old_p,
                db_fetch=db_fetch,
                db_update=db_update,
            )

        return updated

    def _bloom_band_scaling(self, band_diff: int, is_correct: bool) -> float:
        """
        Compute the scaling factor for mastery delta based on the difference between
        the evaluated Bloom level and the student's current mastery band.
        """
        if is_correct:
            scale = 1.0 + 0.3 * band_diff
        else:
            scale = 1.0 - 0.3 * band_diff
        return max(0.2, scale)

    def _propagate_to_ancestors(
        self,
        userid: str,
        skill_id: str,
        delta_p: float,
        db_fetch,
        db_update
    ):
        """
        Propagate probability delta to all ancestor skills via BFS, applying exponential decay at each hop.
        Mastery is always set to 100 * p_learned.
        Stops propagation when the decayed delta_p is below a threshold.
        """
        visited = set()
        queue = deque()
        skill = self.skill_tree.get_skill(skill_id)
        for parent_id in skill.parent_ids:
            queue.append((parent_id, self.ancestor_decay))

        while queue:
            pid, decay = queue.popleft()
            if pid in visited:
                continue
            visited.add(pid)

            anc_delta_p = delta_p * decay
            if abs(anc_delta_p) < self.threshold:
                continue

            state = db_fetch(userid, pid)
            old_p = state['p_learned']
            new_p = max(0.0, min(1.0, old_p + anc_delta_p))
            new_mast = new_p * 100.0

            db_update(userid, pid, new_mast, new_p)

            parent_skill = self.skill_tree.get_skill(pid)
            for grandparent_id in parent_skill.parent_ids:
                if grandparent_id not in visited:
                    queue.append((grandparent_id, decay * self.ancestor_decay))

    def _propagate_to_successors(
        self,
        userid: str,
        skill_id: str,
        delta_p: float,
        db_fetch,
        db_update
    ):
        """
        Propagate probability delta to all child (successor) skills via BFS, applying exponential decay at each hop.
        Mastery is always set to 100 * p_learned.
        Stops propagation when the decayed delta_p is below a threshold.
        """
        visited = set()
        queue = deque()
        skill = self.skill_tree.get_skill(skill_id)
        for child_id in skill.child_ids:
            queue.append((child_id, self.successor_decay))

        while queue:
            cid, decay = queue.popleft()
            if cid in visited:
                continue
            visited.add(cid)

            succ_delta_p = delta_p * decay
            if abs(succ_delta_p) < self.threshold:
                continue

            state = db_fetch(userid, cid)
            old_p = state['p_learned']
            new_p = max(0.0, min(1.0, old_p + succ_delta_p))
            new_mast = new_p * 100.0

            db_update(userid, cid, new_mast, new_p)

            child_skill = self.skill_tree.get_skill(cid)
            for grandchild_id in child_skill.child_ids:
                if grandchild_id not in visited:
                    queue.append((grandchild_id, decay * self.successor_decay))

    # ================================================================== dunder
    def __repr__(self) -> str:
        return (
            f"MasteryUpdater("
            f"scale={self.base_mastery_scale}, "
            f"propagate={self.propagate_to_ancestors}, "
            f"decay={self.ancestor_decay})"
        )
