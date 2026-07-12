"""
skill.py
--------
Defines the Skill node — the fundamental unit of the skill tree.

A Skill without parents is a *prerequisite skill* (root node).
A Skill with one or more parents is a *derived skill*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Skill:
    """
    A single node in the skill DAG.

    Attributes
    ----------
    skill_id    : Globally unique identifier (e.g. "algebra.linear_equations").
    name        : Human-readable short name (e.g. "Solving Linear Equations").
    description : Longer description of what the skill entails.
    topics      : Subject-matter topics this skill is associated with.
                  A skill can belong to multiple topics.
    parent_ids  : IDs of prerequisite skills that must be learned first.
                  Empty → this is a root / prerequisite skill.
    child_ids   : IDs of skills that depend on this skill.
                  Populated automatically by SkillTree.add_prerequisite().
    """
    skill_id:    str
    name:        str
    description: str
    topics:      List[str]
    parent_ids:  List[str] = field(default_factory=list)
    child_ids:   List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ guards
    def __post_init__(self) -> None:
        if not self.skill_id.strip():
            raise ValueError("skill_id must be a non-empty string.")
        if not self.topics:
            raise ValueError(f"Skill '{self.skill_id}' must be associated with at least one topic.")

    # --------------------------------------------------------------- accessors
    @property
    def is_prerequisite(self) -> bool:
        """True if this skill has no prerequisites (i.e. it is a root node)."""
        return len(self.parent_ids) == 0

    @property
    def is_derived(self) -> bool:
        """True if this skill depends on at least one other skill."""
        return len(self.parent_ids) > 0

    def add_parent(self, parent_id: str) -> None:
        """Register a prerequisite. Called by SkillTree — do not call directly."""
        if parent_id not in self.parent_ids:
            self.parent_ids.append(parent_id)

    def add_child(self, child_id: str) -> None:
        """Register a derived skill. Called by SkillTree — do not call directly."""
        if child_id not in self.child_ids:
            self.child_ids.append(child_id)

    # --------------------------------------------------------------- dunder
    def __hash__(self) -> int:
        return hash(self.skill_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Skill) and self.skill_id == other.skill_id

    def __repr__(self) -> str:
        ptype = "root" if self.is_prerequisite else f"derived({self.parent_ids})"
        return f"Skill(id={self.skill_id!r}, type={ptype}, topics={self.topics})"
