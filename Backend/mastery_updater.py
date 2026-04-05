"""
mastery_updater.py
------------------
Policy-aligned mastery updates for a BKT + prerequisite DAG model.

This module implements the policy in `BKT-DAG Policy For Skill Mastery.txt`:

Phase 1 (Bloom-conditioned BKT):
    Guess/slip are chosen from the Bloom level of the question.

Phase 2 (Prerequisite validation):
    If answer is correct on skill C, recursively enforce
        P(parent) >= P(C)
    over all ancestors (pull-up rule).

    If answer is incorrect on skill C, no penalty is propagated to ancestors.

Phase 3 (Successor transition gating):
    For each immediate child S of the updated skill, set transition P(T_S):
        base_transition  if all prerequisites of S are mastered
        locked_transition otherwise

    Conjunctive readiness check uses:
        min(P(prerequisites)) >= mastery_threshold

State contract
--------------
The updater is storage-agnostic and operates via two callbacks:

    db_fetch(userid, skill_id) -> dict
        Expected keys:
            mastery: float in [0, 100]      (optional if p_learned provided)
            p_learned: float in [0, 1]      (optional if mastery provided)
            p_transition: float in [0, 1]   (optional; inferred if missing)

    db_update(userid, skill_id, mastery, p_learned[, p_transition]) -> None
        The updater first tries the 5-argument form (with p_transition).
        If the callback only accepts 4 arguments, it falls back automatically.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, Optional

from bkt import BKTModel, BKTParams
from bloom_taxonomy import BloomLevel
from skill_tree import SkillTree


DbFetch = Callable[[str, str], Dict[str, float]]
DbUpdate = Callable[..., None]


class UpdateMode(Enum):
    DIAGNOSE = auto()
    REGULAR = auto()


@dataclass(frozen=True)
class BloomGuessSlip:
    p_g: float
    p_s: float


@dataclass(frozen=True)
class _SkillState:
    p_learned: float
    mastery: float
    p_transition: float


@dataclass(frozen=True)
class SkillUpdateResult:
    skill_id: str
    old_p_learned: float
    new_p_learned: float
    mastery: float
    bloom_level: BloomLevel
    is_correct: bool
    used_guess: float
    used_slip: float
    used_transition: float
    pulled_up_ancestors: list[str]
    successor_transition_updates: Dict[str, float]


class MasteryUpdater:
    """
    Strict policy implementation for updating a single answered skill or a batch.
    """

    DEFAULT_MASTERY_THRESHOLD: float = 0.95
    DEFAULT_BASE_TRANSITION: float = 0.10
    DEFAULT_DIAGNOSE_BASE_TRANSITION: float = 0.20
    DEFAULT_LOCKED_TRANSITION: float = 0.01

    DEFAULT_BLOOM_GUESS_SLIP: Dict[BloomLevel, BloomGuessSlip] = {
        BloomLevel.REMEMBER:   BloomGuessSlip(p_g=0.30, p_s=0.05),
        BloomLevel.UNDERSTAND: BloomGuessSlip(p_g=0.25, p_s=0.08),
        BloomLevel.APPLY:      BloomGuessSlip(p_g=0.18, p_s=0.12),
        BloomLevel.ANALYZE:    BloomGuessSlip(p_g=0.12, p_s=0.18),
        BloomLevel.EVALUATE:   BloomGuessSlip(p_g=0.08, p_s=0.22),
        BloomLevel.CREATE:     BloomGuessSlip(p_g=0.05, p_s=0.25),
    }

    def __init__(
        self,
        skill_tree: SkillTree,
        mastery_threshold: float = DEFAULT_MASTERY_THRESHOLD,
        base_transition: float = DEFAULT_BASE_TRANSITION,
        diagnose_base_transition: float = DEFAULT_DIAGNOSE_BASE_TRANSITION,
        locked_transition: float = DEFAULT_LOCKED_TRANSITION,
        bloom_guess_slip: Optional[Dict[BloomLevel, BloomGuessSlip]] = None,
    ) -> None:
        if not 0.0 <= mastery_threshold <= 1.0:
            raise ValueError("mastery_threshold must be in [0, 1].")
        for name, value in (
            ("base_transition", base_transition),
            ("diagnose_base_transition", diagnose_base_transition),
            ("locked_transition", locked_transition),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1].")

        self.skill_tree = skill_tree
        self.mastery_threshold = mastery_threshold
        self.base_transition = base_transition
        self.diagnose_base_transition = diagnose_base_transition
        self.locked_transition = locked_transition
        self.bloom_guess_slip = dict(bloom_guess_slip or self.DEFAULT_BLOOM_GUESS_SLIP)

        missing_levels = set(BloomLevel) - set(self.bloom_guess_slip.keys())
        if missing_levels:
            raise ValueError(
                "Missing Bloom guess/slip configuration for levels: "
                + ", ".join(level.name for level in sorted(missing_levels, key=lambda x: x.value))
            )

    # ================================================================== public
    def update_answer(
        self,
        userid: str,
        skill_id: str,
        bloom_level: BloomLevel,
        is_correct: bool,
        db_fetch: DbFetch,
        db_update: DbUpdate,
        mode: UpdateMode = UpdateMode.REGULAR,
        topic: Optional[str] = None,
    ) -> SkillUpdateResult:
        """
        Update one answered skill according to the policy.

        Parameters
        ----------
        userid       : Student identifier used by db_fetch/db_update.
        skill_id     : Answered skill node.
        bloom_level  : Bloom tag attached to the question.
        is_correct   : Whether the submitted answer is correct.
        db_fetch     : Fetch callback.
        db_update    : Update callback.
        mode         : REGULAR/DIAGNOSE, used to choose base transition.
        topic        : Accepted for request compatibility; not used in logic.

        Returns
        -------
        SkillUpdateResult containing direct update details and propagated effects.
        """
        del topic  # topic is currently metadata only; policy logic is skill-centric.

        self._require_skill(skill_id)

        current = self._read_state(userid, skill_id, db_fetch, mode)
        effective_transition = self._compute_transition_for_skill(
            userid=userid,
            skill_id=skill_id,
            db_fetch=db_fetch,
            mode=mode,
        )

        # Keep persisted transition aligned with current prerequisite readiness.
        if abs(effective_transition - current.p_transition) > 1e-12:
            self._write_state(
                userid=userid,
                skill_id=skill_id,
                p_learned=current.p_learned,
                p_transition=effective_transition,
                db_update=db_update,
            )

        params = self._params_for_bloom(bloom_level, effective_transition)
        bkt_model = BKTModel(params)
        new_p = bkt_model.update(current.p_learned, is_correct)

        self._write_state(
            userid=userid,
            skill_id=skill_id,
            p_learned=new_p,
            p_transition=effective_transition,
            db_update=db_update,
        )

        # Phase 2A: Correct answers pull ancestors up to at least child probability.
        pulled_up_ancestors: list[str] = []
        if is_correct:
            pulled_up_ancestors = self._pull_up_ancestors(
                userid=userid,
                skill_id=skill_id,
                floor_p=new_p,
                db_fetch=db_fetch,
                db_update=db_update,
                mode=mode,
            )

        # Phase 3: Recompute transition gates for immediate successors.
        successor_transition_updates = self._refresh_immediate_successor_transitions(
            userid=userid,
            skill_id=skill_id,
            db_fetch=db_fetch,
            db_update=db_update,
            mode=mode,
        )

        return SkillUpdateResult(
            skill_id=skill_id,
            old_p_learned=current.p_learned,
            new_p_learned=new_p,
            mastery=new_p * 100.0,
            bloom_level=bloom_level,
            is_correct=is_correct,
            used_guess=params.p_g,
            used_slip=params.p_s,
            used_transition=effective_transition,
            pulled_up_ancestors=pulled_up_ancestors,
            successor_transition_updates=successor_transition_updates,
        )

    def update_skills(
        self,
        userid: str,
        skills: list[str],
        bloom_levels: list[BloomLevel],
        is_correct: bool,
        db_fetch: DbFetch,
        db_update: DbUpdate,
        mode: UpdateMode = UpdateMode.REGULAR,
        topics: Optional[list[Optional[str]]] = None,
    ) -> list[SkillUpdateResult]:
        """
        Batch wrapper over update_answer for multi-tagged questions.
        """
        if len(skills) != len(bloom_levels):
            raise ValueError("skills and bloom_levels must have the same length.")
        if topics is not None and len(topics) != len(skills):
            raise ValueError("topics must be None or have same length as skills.")

        results: list[SkillUpdateResult] = []
        for idx, skill_id in enumerate(skills):
            topic = topics[idx] if topics else None
            results.append(
                self.update_answer(
                    userid=userid,
                    skill_id=skill_id,
                    bloom_level=bloom_levels[idx],
                    is_correct=is_correct,
                    db_fetch=db_fetch,
                    db_update=db_update,
                    mode=mode,
                    topic=topic,
                )
            )
        return results

    # ================================================================== private
    def _params_for_bloom(self, bloom_level: BloomLevel, p_t: float) -> BKTParams:
        profile = self.bloom_guess_slip[bloom_level]
        return BKTParams(
            p_l0=0.0,
            p_t=p_t,
            p_s=profile.p_s,
            p_g=profile.p_g,
        )

    def _read_state(
        self,
        userid: str,
        skill_id: str,
        db_fetch: DbFetch,
        mode: UpdateMode,
    ) -> _SkillState:
        raw = db_fetch(userid, skill_id) or {}

        p_learned = raw.get("p_learned")
        mastery = raw.get("mastery")

        if p_learned is None and mastery is None:
            p_learned = 0.0
            mastery = 0.0
        elif p_learned is None:
            p_learned = float(mastery) / 100.0
        elif mastery is None:
            mastery = float(p_learned) * 100.0

        p_learned = self._clamp01(float(p_learned))
        mastery = self._clamp100(float(mastery))

        p_transition = raw.get("p_transition")
        if p_transition is None:
            p_transition = self._compute_transition_for_skill(
                userid=userid,
                skill_id=skill_id,
                db_fetch=db_fetch,
                mode=mode,
            )
        p_transition = self._clamp01(float(p_transition))

        return _SkillState(
            p_learned=p_learned,
            mastery=mastery,
            p_transition=p_transition,
        )

    def _pull_up_ancestors(
        self,
        userid: str,
        skill_id: str,
        floor_p: float,
        db_fetch: DbFetch,
        db_update: DbUpdate,
        mode: UpdateMode,
    ) -> list[str]:
        """
        Recursively enforce P(ancestor) >= floor_p for all ancestors of skill_id.
        """
        visited: set[str] = set()
        updated: list[str] = []

        skill = self._require_skill(skill_id)
        queue: deque[str] = deque(skill.parent_ids)

        while queue:
            ancestor_id = queue.popleft()
            if ancestor_id in visited:
                continue
            visited.add(ancestor_id)

            state = self._read_state(userid, ancestor_id, db_fetch, mode)
            promoted_p = max(state.p_learned, floor_p)

            if promoted_p > state.p_learned + 1e-12:
                self._write_state(
                    userid=userid,
                    skill_id=ancestor_id,
                    p_learned=promoted_p,
                    p_transition=state.p_transition,
                    db_update=db_update,
                )
                updated.append(ancestor_id)

            ancestor = self._require_skill(ancestor_id)
            for parent_id in ancestor.parent_ids:
                if parent_id not in visited:
                    queue.append(parent_id)

        return updated

    def _refresh_immediate_successor_transitions(
        self,
        userid: str,
        skill_id: str,
        db_fetch: DbFetch,
        db_update: DbUpdate,
        mode: UpdateMode,
    ) -> Dict[str, float]:
        """
        Recalculate P(T) for each immediate child of skill_id using conjunctive gating.
        """
        updates: Dict[str, float] = {}

        skill = self._require_skill(skill_id)
        for child_id in skill.child_ids:
            state = self._read_state(userid, child_id, db_fetch, mode)
            new_p_transition = self._compute_transition_for_skill(
                userid=userid,
                skill_id=child_id,
                db_fetch=db_fetch,
                mode=mode,
            )

            if abs(new_p_transition - state.p_transition) > 1e-12:
                self._write_state(
                    userid=userid,
                    skill_id=child_id,
                    p_learned=state.p_learned,
                    p_transition=new_p_transition,
                    db_update=db_update,
                )
                updates[child_id] = new_p_transition

        return updates

    def _compute_transition_for_skill(
        self,
        userid: str,
        skill_id: str,
        db_fetch: DbFetch,
        mode: UpdateMode,
    ) -> float:
        """
        Conjunctive readiness gate:
            base transition if all prerequisites >= mastery_threshold,
            otherwise locked transition.
        """
        skill = self._require_skill(skill_id)
        base_transition = self._base_transition(mode)

        if not skill.parent_ids:
            return base_transition

        min_prereq = 1.0
        for parent_id in skill.parent_ids:
            parent_state = db_fetch(userid, parent_id) or {}
            parent_p = parent_state.get("p_learned")
            if parent_p is None:
                parent_mastery = parent_state.get("mastery", 0.0)
                parent_p = float(parent_mastery) / 100.0
            min_prereq = min(min_prereq, self._clamp01(float(parent_p)))

        if min_prereq >= self.mastery_threshold:
            return base_transition
        return self.locked_transition

    def _write_state(
        self,
        userid: str,
        skill_id: str,
        p_learned: float,
        p_transition: float,
        db_update: DbUpdate,
    ) -> None:
        p_learned = self._clamp01(p_learned)
        p_transition = self._clamp01(p_transition)
        mastery = p_learned * 100.0

        try:
            db_update(userid, skill_id, mastery, p_learned, p_transition)
        except TypeError:
            # Backward-compatible path for stores that don't persist p_transition yet.
            db_update(userid, skill_id, mastery, p_learned)

    def _base_transition(self, mode: UpdateMode) -> float:
        if mode == UpdateMode.DIAGNOSE:
            return self.diagnose_base_transition
        return self.base_transition

    def _require_skill(self, skill_id: str):
        skill = self.skill_tree.get_skill(skill_id)
        if skill is None:
            raise KeyError(f"Skill '{skill_id}' not found in skill tree.")
        return skill

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _clamp100(value: float) -> float:
        return max(0.0, min(100.0, value))

    def __repr__(self) -> str:
        return (
            "MasteryUpdater("
            f"threshold={self.mastery_threshold}, "
            f"base_transition={self.base_transition}, "
            f"locked_transition={self.locked_transition}"
            ")"
        )
