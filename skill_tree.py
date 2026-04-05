"""
skill_tree.py
-------------
A Directed Acyclic Graph (DAG) of Skill nodes.

Edges represent prerequisite relationships:
    parent  ──►  child
    (must know)  (derived skill)

Key responsibilities:
  • Enforce no-cycle invariant via DFS on every edge insertion.
  • Maintain a topic → [skill_id] reverse index for fast topic lookup.
  • Expose BFS/DFS traversal utilities and topological ordering (Kahn's algorithm).
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterator, List, Optional

from skill import Skill


class SkillTree:
    """
    A DAG where nodes are Skills and directed edges encode prerequisite relationships.

    Usage
    -----
    >>> tree = SkillTree()
    >>> tree.add_skill(Skill("s1", "Addition", "...", ["arithmetic"]))
    >>> tree.add_skill(Skill("s2", "Multiplication", "...", ["arithmetic"]))
    >>> tree.add_prerequisite(child_id="s2", parent_id="s1")
    """

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}
        # Reverse index: topic → list[skill_id]
        self._topic_index: Dict[str, List[str]] = defaultdict(list)

    # ================================================================== mutators
    def add_skill(self, skill: Skill) -> None:
        """
        Register a skill in the tree.

        Raises
        ------
        ValueError  If a skill with the same skill_id already exists.
        """
        if skill.skill_id in self._skills:
            raise ValueError(f"Skill '{skill.skill_id}' already exists in the tree.")
        self._skills[skill.skill_id] = skill
        for topic in skill.topics:
            self._topic_index[topic].append(skill.skill_id)

    def add_prerequisite(self, child_id: str, parent_id: str) -> None:
        """
        Declare that `parent_id` must be learned before `child_id`.

        The edge parent → child is only added if it does not create a cycle.

        Raises
        ------
        KeyError    If either skill_id is not in the tree.
        ValueError  If the edge would create a cycle.
        """
        child  = self._require(child_id)
        parent = self._require(parent_id)

        # Idempotent: skip if the edge already exists.
        if parent_id in child.parent_ids:
            return

        # Tentatively add the edge, then check for cycles.
        child.add_parent(parent_id)
        parent.add_child(child_id)

        if self._has_cycle():
            # Roll back to preserve invariant.
            child.parent_ids.remove(parent_id)
            parent.child_ids.remove(child_id)
            raise ValueError(
                f"Adding prerequisite '{parent_id}' → '{child_id}' "
                f"would introduce a cycle in the skill tree."
            )

    # ================================================================== queries
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Return the Skill for `skill_id`, or None if it doesn't exist."""
        return self._skills.get(skill_id)

    def get_skills_for_topic(self, topic: str) -> List[Skill]:
        """Return all skills associated with a given topic."""
        return [self._skills[sid] for sid in self._topic_index.get(topic, [])]

    def get_all_topics(self) -> List[str]:
        """Return a sorted list of all registered topics."""
        return sorted(self._topic_index.keys())

    def get_root_skills(self) -> List[Skill]:
        """Return all prerequisite (root) skills — those with no parents."""
        return [s for s in self._skills.values() if s.is_prerequisite]

    def get_direct_parents(self, skill_id: str) -> List[Skill]:
        """Return immediate prerequisite skills of `skill_id`."""
        skill = self._require(skill_id)
        return [self._skills[pid] for pid in skill.parent_ids]

    def get_direct_children(self, skill_id: str) -> List[Skill]:
        """Return skills that directly depend on `skill_id`."""
        skill = self._require(skill_id)
        return [self._skills[cid] for cid in skill.child_ids]

    def get_all_ancestors(self, skill_id: str) -> List[Skill]:
        """
        Return every ancestor of `skill_id` (all transitive prerequisites)
        via BFS, without duplicates.
        """
        self._require(skill_id)
        visited: set[str] = set()
        queue: deque[str] = deque(self._skills[skill_id].parent_ids)
        while queue:
            pid = queue.popleft()
            if pid in visited:
                continue
            visited.add(pid)
            queue.extend(self._skills[pid].parent_ids)
        return [self._skills[pid] for pid in visited]

    def get_all_descendants(self, skill_id: str) -> List[Skill]:
        """
        Return every descendant of `skill_id` (all skills that transitively
        depend on it) via BFS, without duplicates.
        """
        self._require(skill_id)
        visited: set[str] = set()
        queue: deque[str] = deque(self._skills[skill_id].child_ids)
        while queue:
            cid = queue.popleft()
            if cid in visited:
                continue
            visited.add(cid)
            queue.extend(self._skills[cid].child_ids)
        return [self._skills[cid] for cid in visited]

    def topological_order(self) -> List[Skill]:
        """
        Return all skills in topological order (Kahn's algorithm).
        Root skills appear first; leaf-derived skills appear last.

        Raises
        ------
        RuntimeError  If the tree contains a cycle (should never happen if
                      add_prerequisite is always used, but guards against
                      manual state corruption).
        """
        in_degree: Dict[str, int] = {
            sid: len(skill.parent_ids)
            for sid, skill in self._skills.items()
        }
        queue: deque[str] = deque(
            sid for sid, deg in in_degree.items() if deg == 0
        )
        result: List[Skill] = []

        while queue:
            sid = queue.popleft()
            result.append(self._skills[sid])
            for cid in self._skills[sid].child_ids:
                in_degree[cid] -= 1
                if in_degree[cid] == 0:
                    queue.append(cid)

        if len(result) != len(self._skills):
            raise RuntimeError(
                "Cycle detected during topological sort — the skill tree is corrupted."
            )
        return result

    # ================================================================== dunder
    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[Skill]:
        """Iterate over all skills in insertion order."""
        return iter(self._skills.values())

    def __repr__(self) -> str:
        return f"SkillTree({len(self._skills)} skills, {len(self._topic_index)} topics)"

    # ================================================================== private
    def _require(self, skill_id: str) -> Skill:
        """Return the skill or raise KeyError."""
        try:
            return self._skills[skill_id]
        except KeyError:
            raise KeyError(f"Skill '{skill_id}' not found in the skill tree.")

    def _has_cycle(self) -> bool:
        """
        Detect cycles via DFS with three-colour marking
        (WHITE=unvisited, GRAY=in-stack, BLACK=done).
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        colour: Dict[str, int] = {sid: WHITE for sid in self._skills}

        def dfs(node: str) -> bool:
            colour[node] = GRAY
            for child_id in self._skills[node].child_ids:
                if colour[child_id] == GRAY:
                    return True          # back-edge → cycle
                if colour[child_id] == WHITE and dfs(child_id):
                    return True
            colour[node] = BLACK
            return False

        return any(
            dfs(sid)
            for sid in self._skills
            if colour[sid] == WHITE
        )
