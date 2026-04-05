"""
student_model.py
----------------
Maintains the internal knowledge model for a single student.

For every skill the student has interacted with, the model tracks two quantities:

    mastery     (float, 0–100)
        A composite score reflecting both *what* the student knows and *how deeply*
        they know it (Bloom's level).  The band in which this score lies indicates
        the Bloom level the student has reached for that skill:

            0.00 – 16.67  → REMEMBER
            16.67 – 33.33 → UNDERSTAND
            33.33 – 50.00 → APPLY
            50.00 – 66.67 → ANALYZE
            66.67 – 83.33 → EVALUATE
            83.33 – 100.0 → CREATE

    p_learned   (float, 0–1)
        BKT posterior probability of having learned the skill.
        Updated by BKTModel and used as the primary learning signal.

The model is intentionally separated from the update logic so that either can be
replaced independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bloom_taxonomy import BloomLevel, get_level_from_mastery
from bkt import BKTParams


# ---------------------------------------------------------------------------
# Per-skill state container
# ---------------------------------------------------------------------------
@dataclass
class SkillState:
    """
    Snapshot of a student's knowledge state for one skill.

    Attributes
    ----------
    skill_id           : Identifies which skill this state belongs to.
    mastery            : Composite mastery score in [0, 100].
    p_learned          : BKT P(Lₙ) in [0, 1].
    bloom_level_reached: Bloom level corresponding to current mastery score.
    attempts           : Total number of questions answered for this skill.
    correct_attempts   : Number of correct answers for this skill.
    """
    skill_id:            str
    mastery:             float = 0.0
    p_learned:           float = 0.0
    bloom_level_reached: BloomLevel = BloomLevel.REMEMBER
    attempts:            int = 0
    correct_attempts:    int = 0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not 0.0 <= self.mastery <= 100.0:
            raise ValueError(f"mastery must be in [0, 100], got {self.mastery}.")
        if not 0.0 <= self.p_learned <= 1.0:
            raise ValueError(f"p_learned must be in [0, 1], got {self.p_learned}.")

    @property
    def accuracy(self) -> float:
        """Fraction of correct answers (0 if no attempts)."""
        return self.correct_attempts / self.attempts if self.attempts else 0.0

    def __repr__(self) -> str:
        return (
            f"SkillState(skill={self.skill_id!r}, "
            f"mastery={self.mastery:.1f}, "
            f"p_learned={self.p_learned:.3f}, "
            f"bloom={self.bloom_level_reached.name})"
        )


# ---------------------------------------------------------------------------
# Student model
# ---------------------------------------------------------------------------
class StudentModel:
    """
    Knowledge model for a single student across all skills.

    Responsibilities
    ----------------
    • Lazily initialise SkillState for skills the student has not yet seen.
    • Provide clean read/write accessors so MasteryUpdater never touches
      internal dicts directly.
    • Enforce invariants (clamp values) on every write.
    • Allow per-skill BKT parameter overrides (e.g. different prior for easier skills).

    Design note
    -----------
    This class is intentionally dumb about *how* mastery changes — that logic
    lives in MasteryUpdater.  StudentModel only stores and validates state.
    """

    def __init__(
        self,
        student_id: str,
        default_bkt_params: Optional[BKTParams] = None,
    ) -> None:
        self.student_id = student_id
        self._default_bkt_params: BKTParams = default_bkt_params or BKTParams.default()
        self._skill_states: Dict[str, SkillState] = {}
        self._skill_bkt_overrides: Dict[str, BKTParams] = {}

    # ================================================================== read API
    def get_skill_state(self, skill_id: str) -> SkillState:
        """
        Return the SkillState for `skill_id`.
        If the student has never interacted with this skill before, a fresh
        state is created using the BKT prior P(L₀).
        """
        if skill_id not in self._skill_states:
            p_l0 = self._resolve_bkt_params(skill_id).p_l0
            self._skill_states[skill_id] = SkillState(
                skill_id=skill_id,
                mastery=0.0,
                p_learned=p_l0,
                bloom_level_reached=BloomLevel.REMEMBER,
            )
        return self._skill_states[skill_id]

    def get_mastery(self, skill_id: str) -> float:
        """Return mastery score (0–100) for the skill."""
        return self.get_skill_state(skill_id).mastery

    def get_p_learned(self, skill_id: str) -> float:
        """Return BKT P(learned) for the skill."""
        return self.get_skill_state(skill_id).p_learned

    def get_bloom_level(self, skill_id: str) -> BloomLevel:
        """Return the Bloom level corresponding to current mastery."""
        return self.get_skill_state(skill_id).bloom_level_reached

    def get_bkt_params(self, skill_id: str) -> BKTParams:
        """Return BKT params for this skill (override if set, else default)."""
        return self._resolve_bkt_params(skill_id)

    def is_skill_accessible(
        self,
        skill_id: str,
        skill_tree,
        mastery_threshold: float = 50.0,
    ) -> bool:
        """
        Return True if all direct prerequisites of `skill_id` have mastery
        at or above `mastery_threshold`.

        Parameters
        ----------
        skill_tree         : The SkillTree instance to resolve parent IDs.
        mastery_threshold  : Minimum mastery required to unlock derived skills
                             (default 50 = APPLY band lower bound).
        """
        skill = skill_tree.get_skill(skill_id)
        if skill is None:
            return False
        return all(
            self.get_mastery(pid) >= mastery_threshold
            for pid in skill.parent_ids
        )

    def all_skill_ids(self) -> List[str]:
        """Return IDs of all skills the student has encountered."""
        return list(self._skill_states.keys())

    # ================================================================== write API
    def update_skill_state(
        self,
        skill_id: str,
        new_mastery: float,
        new_p_learned: float,
        is_correct: bool,
    ) -> SkillState:
        """
        Overwrite the skill state with new values.
        Values are clamped to their valid ranges before storage.

        Called exclusively by MasteryUpdater — client code should not call this.
        """
        state = self.get_skill_state(skill_id)      # ensure state exists
        state.mastery    = max(0.0, min(100.0, new_mastery))
        state.p_learned  = max(0.0, min(1.0,  new_p_learned))
        state.bloom_level_reached = get_level_from_mastery(state.mastery)
        state.attempts  += 1
        if is_correct:
            state.correct_attempts += 1
        return state

    def set_bkt_params(self, skill_id: str, params: BKTParams) -> None:
        """Override BKT parameters for a specific skill."""
        self._skill_bkt_overrides[skill_id] = params

    # ================================================================== reporting
    def summary(self) -> Dict[str, dict]:
        """
        Return a JSON-serialisable snapshot of all skill states.
        Useful for logging, dashboards, and testing.
        """
        return {
            sid: {
                "mastery":      round(state.mastery, 2),
                "p_learned":    round(state.p_learned, 4),
                "bloom_level":  state.bloom_level_reached.name,
                "attempts":     state.attempts,
                "accuracy":     round(state.accuracy, 4),
            }
            for sid, state in self._skill_states.items()
        }

    # ================================================================== private
    def _resolve_bkt_params(self, skill_id: str) -> BKTParams:
        return self._skill_bkt_overrides.get(skill_id, self._default_bkt_params)

    # ================================================================== dunder
    def __repr__(self) -> str:
        return (
            f"StudentModel(student_id={self.student_id!r}, "
            f"skills_seen={len(self._skill_states)})"
        )
