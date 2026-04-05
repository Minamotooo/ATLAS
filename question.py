"""
question.py
-----------
Represents a single MCQ question tagged with its pedagogical metadata:
    (topic, bloom_level, skill_ids)

This is the 3-tuple that drives all mastery updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from bloom_taxonomy import BloomLevel


@dataclass
class Question:
    """
    A multiple-choice question with full pedagogical tagging.

    Attributes
    ----------
    question_id   : Unique identifier.
    text          : The question stem shown to the student.
    options       : Ordered list of answer choices (index 0 = option A, etc.).
    correct_index : Index into `options` of the correct answer.
    topic         : The subject area this question belongs to.
    bloom_level   : Bloom's Taxonomy cognitive level required to answer correctly.
    skill_ids     : Skills exercised by this question (≥ 1).  These must exist
                    in the SkillTree before the question is used.
    """
    question_id:   str
    text:          str
    options:       List[str]
    correct_index: int
    topic:         str
    bloom_level:   BloomLevel
    skill_ids:     List[str]

    # ------------------------------------------------------------------ guards
    def __post_init__(self) -> None:
        if not self.options:
            raise ValueError("A question must have at least one option.")
        if not (0 <= self.correct_index < len(self.options)):
            raise ValueError(
                f"correct_index {self.correct_index} is out of range for "
                f"{len(self.options)} options."
            )
        if not self.skill_ids:
            raise ValueError("A question must be tagged with at least one skill.")
        if not self.topic.strip():
            raise ValueError("topic must be a non-empty string.")

    # --------------------------------------------------------------- accessors
    @property
    def correct_answer(self) -> str:
        """The text of the correct answer option."""
        return self.options[self.correct_index]

    def is_correct(self, chosen_index: int) -> bool:
        """Return True if the student's chosen index matches the correct answer."""
        return chosen_index == self.correct_index

    # --------------------------------------------------------------- dunder
    def __repr__(self) -> str:
        return (
            f"Question(id={self.question_id!r}, topic={self.topic!r}, "
            f"bloom={self.bloom_level.name}, skills={self.skill_ids})"
        )
