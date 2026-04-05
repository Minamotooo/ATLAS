"""
diagnostic.py
-------------
Adaptive diagnostic session for rapidly estimating a student's mastery
profile across the entire skill DAG in as few questions as possible.

State contract (matches mastery_updater.py)
-------------------------------------------
All student state is read and written exclusively through two callbacks:

    db_fetch(userid, skill_id) -> {'mastery': float, 'p_learned': float}
    db_update(userid, skill_id, mastery: float, p_learned: float) -> None

Mastery and p_learned are always kept in sync:
    mastery = p_learned × 100

This matches the convention established in MasteryUpdater.

Algorithm
---------
1.  INIT
    Write a depth-based prior to every skill via db_update:
        root skills  (depth 0) → DEFAULT_MASTERY_ROOT  (70%)
        deepest skills         → DEFAULT_MASTERY_LEAF  (20%)
    p_learned is set to mastery / 100.

2.  SELECT SKILL
    Among all untested skills, pick the one whose count of unknown ancestors
    and unknown descendants is most balanced (weighted-median strategy):

        score(node) = 1 / (1 + |unknown_ancestors − unknown_descendants|)

3.  SELECT BLOOM LEVEL
    Derive the skill's current Bloom level from p_learned × 100, then
    test one level above (Zone of Proximal Development), clamped to CREATE.

4.  SELECT TOPIC
    Return a random topic from the skill's topic list.

5.  RECORD ANSWER  (each skill tested at most once)

    a.  Compute new p_learned from the Bloom band midpoint:
            correct   → midpoint of the tested Bloom band  / 100
            incorrect → midpoint of the band one level below / 100
        Write via db_update.

    b.  Compute delta_p = new_p - old_p.

    c.  Propagate delta_p to ANCESTORS:
            correct   → large positive delta   (decays with hop distance)
            incorrect → small negative delta   (decays with hop distance)

    d.  Propagate delta_p to DESCENDANTS:
            correct   → small positive delta   (decays with hop distance)
            incorrect → large negative delta   (decays with hop distance)

    Propagation stops when |decayed_delta_p| < threshold.
    BFS ensures each node is updated at most once per propagation pass.

6.  STOP
    When the fraction of untested skills falls below stop_threshold (default
    15%), the remaining unknowns are left at their propagated estimates.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Callable, Dict, NamedTuple, Optional, Tuple

from bloom_taxonomy import BloomLevel, get_band, get_level_from_mastery
from skill_tree import SkillTree


# ---------------------------------------------------------------------------
# Type aliases (mirror mastery_updater.py's calling convention)
# ---------------------------------------------------------------------------
DbFetch  = Callable[[str, str], Dict[str, float]]          # (userid, skill_id) → state
DbUpdate = Callable[[str, str, float, float], None]         # (userid, skill_id, mastery, p_learned)


# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------
_DEFAULT_MASTERY_ROOT: float = 70.0   # prior mastery % for root (depth-0) skills
_DEFAULT_MASTERY_LEAF: float = 20.0   # prior mastery % for deepest skills
_BASE_DELTA_P_LARGE:   float = 0.25   # primary propagation delta   (p_learned units)
_BASE_DELTA_P_SMALL:   float = 0.10   # secondary propagation delta (p_learned units)
_PROPAGATION_DECAY:    float = 0.50   # exponential decay per hop
_DECAY_THRESHOLD:      float = 0.01   # matches MasteryUpdater.DEFAULT_DECAY_THRESHOLD
_STOP_THRESHOLD:       float = 0.15   # stop when < 15% of skills remain untested


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------
class QuestionSpec(NamedTuple):
    """
    The (topic, skill_id, bloom_level) triple consumed by the question generator.
    """
    topic:       str
    skill_id:    str
    bloom_level: BloomLevel


# ---------------------------------------------------------------------------
# Diagnostic session
# ---------------------------------------------------------------------------
class DiagnosticSession:
    """
    A single fast diagnostic pass over the skill DAG for one student.

    Each skill is tested at most once.  The session terminates early once
    the fraction of untested skills drops below stop_threshold.

    Parameters
    ----------
    skill_tree      : The shared SkillTree for this session.
    userid          : Student identifier, forwarded to db_fetch / db_update.
    db_fetch        : Callable(userid, skill_id) → {'mastery': float, 'p_learned': float}
    db_update       : Callable(userid, skill_id, mastery, p_learned) → None
    stop_threshold  : Session ends when the untested fraction drops below this.
    base_large_p    : Primary propagation magnitude in p_learned units.
    base_small_p    : Secondary propagation magnitude in p_learned units.
    decay           : Exponential decay factor per hop.
    threshold       : Propagation stops when |delta_p| drops below this value.

    Usage
    -----
    >>> session = DiagnosticSession(skill_tree, userid, db_fetch, db_update)
    >>> while not session.is_complete():
    ...     spec = session.next_question_spec()
    ...     # generate and present question from spec ...
    ...     session.record_answer(spec.skill_id, spec.bloom_level, is_correct)
    >>> profile = session.mastery_snapshot()
    """

    def __init__(
        self,
        skill_tree:     SkillTree,
        userid:         str,
        db_fetch:       DbFetch,
        db_update:      DbUpdate,
        stop_threshold: float = _STOP_THRESHOLD,
        base_large_p:   float = _BASE_DELTA_P_LARGE,
        base_small_p:   float = _BASE_DELTA_P_SMALL,
        decay:          float = _PROPAGATION_DECAY,
        threshold:      float = _DECAY_THRESHOLD,
    ) -> None:
        if not 0.0 <= stop_threshold < 1.0:
            raise ValueError("stop_threshold must be in [0, 1).")
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be in (0, 1].")

        self.skill_tree     = skill_tree
        self.userid         = userid
        self.db_fetch       = db_fetch
        self.db_update      = db_update
        self.stop_threshold = stop_threshold
        self.base_large_p   = base_large_p
        self.base_small_p   = base_small_p
        self.decay          = decay
        self.threshold      = threshold

        # True once record_answer() has been called for that skill.
        self.tested: Dict[str, bool] = {
            skill.skill_id: False for skill in skill_tree
        }

        self._depths:    Dict[str, int] = _compute_depths(skill_tree)
        self._max_depth: int = max(self._depths.values(), default=0)

        self._initialise_mastery()

    # ================================================================== public
    def is_complete(self) -> bool:
        """
        Return True when the session should end.
        Triggers when every skill is tested, or the untested fraction is
        below stop_threshold.
        """
        untested = sum(1 for done in self.tested.values() if not done)
        total    = len(self.tested)
        if total == 0:
            return True
        return untested == 0 or (untested / total) < self.stop_threshold

    def next_question_spec(self) -> Optional[QuestionSpec]:
        """
        Return the (topic, skill_id, bloom_level) triple for the next question.
        Returns None if the session is already complete.
        """
        if self.is_complete():
            return None

        skill_id    = self._select_skill()
        bloom_level = self._select_bloom(skill_id)
        topic       = self._select_topic(skill_id)

        return QuestionSpec(topic=topic, skill_id=skill_id, bloom_level=bloom_level)

    def record_answer(
        self,
        skill_id:    str,
        bloom_level: BloomLevel,
        is_correct:  bool,
    ) -> None:
        """
        Record the student's answer and update the mastery model.

        Raises
        ------
        KeyError    If skill_id is not in the skill tree.
        ValueError  If this skill has already been tested this session.
        """
        if skill_id not in self.tested:
            raise KeyError(f"Skill '{skill_id}' not found in the skill tree.")
        if self.tested[skill_id]:
            raise ValueError(
                f"Skill '{skill_id}' has already been tested in this session."
            )

        # ---- 1. Set the directly-tested skill -----------------------------
        old_p = self.db_fetch(self.userid, skill_id)['p_learned']

        if is_correct:
            new_mastery = _band_midpoint(bloom_level)
        else:
            lower_level = BloomLevel(max(1, bloom_level.value - 1))
            new_mastery = _band_midpoint(lower_level)

        new_p = new_mastery / 100.0
        self.db_update(self.userid, skill_id, new_mastery, new_p)
        self.tested[skill_id] = True

        # >>> START OF INSERTED FIX <<<
        # If correct, assume mastery of all prerequisites (ancestors).
        # If incorrect, assume non-mastery of all advanced concepts (descendants).
        if is_correct:
            for anc in self.skill_tree.get_all_ancestors(skill_id):
                self.tested[anc.skill_id] = True
        else:
            for desc in self.skill_tree.get_all_descendants(skill_id):
                self.tested[desc.skill_id] = True
        # >>> END OF INSERTED FIX <<<

        delta_p = new_p - old_p

        # ---- 2. Ancestors: large if correct, small if incorrect -----------
        anc_base = self.base_large_p if is_correct else -self.base_small_p
        self._propagate(skill_id, anc_base, direction="up")

        # ---- 3. Descendants: small if correct, large if incorrect ---------
        desc_base = self.base_small_p if is_correct else -self.base_large_p
        self._propagate(skill_id, desc_base, direction="down")

    def mastery_snapshot(self) -> Dict[str, float]:
        """
        Return a {skill_id: mastery} mapping for every skill.
        Reads live from db_fetch so values reflect all propagation.
        """
        return {
            skill.skill_id: round(
                self.db_fetch(self.userid, skill.skill_id)['mastery'], 2
            )
            for skill in self.skill_tree
        }

    def progress(self) -> Tuple[int, int]:
        """Return (tested_count, total_count)."""
        tested = sum(self.tested.values())
        return tested, len(self.tested)

    # ================================================================== private: init
    def _initialise_mastery(self) -> None:
        """Write a depth-based mastery prior for every skill via db_update."""
        for skill in self.skill_tree:
            sid     = skill.skill_id
            mastery = _depth_to_mastery(self._depths[sid], self._max_depth)
            p       = mastery / 100.0
            self.db_update(self.userid, sid, mastery, p)

    # ================================================================== private: selection
    def _select_skill(self) -> str:
        """
        Pick the untested skill that best splits the remaining unknown set.
        Maximises 1 / (1 + |unknown_ancestors − unknown_descendants|).
        """
        untested_ids = {sid for sid, done in self.tested.items() if not done}

        best_id:    Optional[str] = None
        best_score: float         = -1.0

        for sid in untested_ids:
            unknown_anc  = sum(
                1 for s in self.skill_tree.get_all_ancestors(sid)
                if not self.tested[s.skill_id]
            )
            unknown_desc = sum(
                1 for s in self.skill_tree.get_all_descendants(sid)
                if not self.tested[s.skill_id]
            )
            # score = 1.0 / (1.0 + abs(unknown_anc - unknown_desc)) 
            # The "Balanced Volume" heuristic
            # Adding 1 to the numerator ensures nodes with 0 relatives 
            # still have a positive score.
            score = (unknown_anc + unknown_desc + 1) / (1.0 + abs(unknown_anc - unknown_desc))
            if score > best_score:
                best_score = score
                best_id    = sid

        return best_id or next(iter(untested_ids))

    def _select_bloom(self, skill_id: str) -> BloomLevel:
        """One Bloom level above current mastery estimate, clamped to CREATE."""
        p_learned     = self.db_fetch(self.userid, skill_id)['p_learned']
        current_level = get_level_from_mastery(p_learned * 100.0)
        next_val      = min(current_level.value + 1, max(b.value for b in BloomLevel))
        return BloomLevel(next_val)

    def _select_topic(self, skill_id: str) -> str:
        """Random topic from the skill's topic list."""
        return random.choice(self.skill_tree.get_skill(skill_id).topics)

    # ================================================================== private: propagation
    def _propagate(
        self,
        skill_id:  str,
        base_p:    float,   # signed magnitude in p_learned units
        direction: str,     # "up" = ancestors, "down" = descendants
    ) -> None:
        """
        BFS propagation of a decayed delta_p in the given direction.

        `base_p` encodes sign (positive = boost, negative = penalty) and
        primary/secondary magnitude.  Decay is applied per hop.
        Propagation stops when |decayed delta_p| < threshold. ??
        BFS means diamond-shaped DAGs are handled without double-counting.
        """
        visited: set[str] = set()
        queue: deque[Tuple[str, float]] = deque()

        start    = self.skill_tree.get_skill(skill_id)
        seed_ids = start.parent_ids if direction == "up" else start.child_ids
        for nid in seed_ids:
            queue.append((nid, self.decay))   # first hop already decayed

        while queue:
            nid, decay_factor = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)

            delta_p = base_p * decay_factor
            if abs(delta_p) < self.threshold:
                continue

            state = self.db_fetch(self.userid, nid)
            old_p = state['p_learned']
            new_p = max(0.0, min(1.0, old_p + delta_p))
            self.db_update(self.userid, nid, new_p * 100.0, new_p)

            node     = self.skill_tree.get_skill(nid)
            next_ids = node.parent_ids if direction == "up" else node.child_ids
            for next_id in next_ids:
                if next_id not in visited:
                    queue.append((next_id, decay_factor * self.decay))

    # ================================================================== dunder
    def __repr__(self) -> str:
        tested, total = self.progress()
        return (
            f"DiagnosticSession("
            f"userid={self.userid!r}, "
            f"progress={tested}/{total}, "
            f"complete={self.is_complete()})"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _compute_depths(skill_tree: SkillTree) -> Dict[str, int]:
    """Longest path from any root to each node, in topological order."""
    depths: Dict[str, int] = {}
    for skill in skill_tree.topological_order():
        sid = skill.skill_id
        depths[sid] = (
            0 if not skill.parent_ids
            else 1 + max(depths[pid] for pid in skill.parent_ids)
        )
    return depths


def _depth_to_mastery(depth: int, max_depth: int) -> float:
    """Linear interpolation: depth 0 → ROOT%, max_depth → LEAF%."""
    if max_depth == 0:
        return _DEFAULT_MASTERY_ROOT
    ratio = depth / max_depth
    return _DEFAULT_MASTERY_ROOT - (_DEFAULT_MASTERY_ROOT - _DEFAULT_MASTERY_LEAF) * ratio


def _band_midpoint(level: BloomLevel) -> float:
    """Mastery % at the centre of a Bloom band."""
    band = get_band(level)
    return (band.lower + band.upper) / 2.0