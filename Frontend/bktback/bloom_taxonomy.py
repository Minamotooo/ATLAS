"""
bloom_taxonomy.py
-----------------
Defines Bloom's Taxonomy levels and their corresponding mastery bands
on the 0–100 scale.

Band layout (6 equal bands of ~16.67 points each):
    REMEMBER   :  0.00 – 16.67
    UNDERSTAND : 16.67 – 33.33
    APPLY      : 33.33 – 50.00
    ANALYZE    : 50.00 – 66.67
    EVALUATE   : 66.67 – 83.33
    CREATE     : 83.33 – 100.00
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class BloomLevel(Enum):
    """
    Bloom's Taxonomy cognitive levels, ordered from lowest to highest.
    Integer values allow direct ordinal comparison (REMEMBER < UNDERSTAND < … < CREATE).
    """
    REMEMBER   = 1
    UNDERSTAND = 2
    APPLY      = 3
    ANALYZE    = 4
    EVALUATE   = 5
    CREATE     = 6

    # ------------------------------------------------------------------ helpers
    def __lt__(self, other: BloomLevel) -> bool:
        return self.value < other.value

    def __le__(self, other: BloomLevel) -> bool:
        return self.value <= other.value

    def __gt__(self, other: BloomLevel) -> bool:
        return self.value > other.value

    def __ge__(self, other: BloomLevel) -> bool:
        return self.value >= other.value

    def next_level(self) -> BloomLevel | None:
        """Return the next higher Bloom level, or None if already at CREATE."""
        try:
            return BloomLevel(self.value + 1)
        except ValueError:
            return None


@dataclass(frozen=True)
class BloomBand:
    """
    Maps a Bloom level to its contiguous mastery band [lower, upper].
    Both bounds are inclusive.
    """
    level: BloomLevel
    lower: float   # minimum mastery score in this band
    upper: float   # maximum mastery score in this band

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def contains(self, mastery: float) -> bool:
        return self.lower <= mastery <= self.upper

    def clamp(self, mastery: float) -> float:
        """Clamp a mastery value to lie within this band."""
        return max(self.lower, min(self.upper, mastery))


# ---------------------------------------------------------------------------
# Band registry — single source of truth for all band definitions.
# ---------------------------------------------------------------------------
_BAND_WIDTH = 100.0 / len(BloomLevel)   # ≈ 16.667

BLOOM_BANDS: list[BloomBand] = [
    BloomBand(
        level=level,
        lower=round((level.value - 1) * _BAND_WIDTH, 4),
        upper=round( level.value      * _BAND_WIDTH, 4),
    )
    for level in BloomLevel
]

# Fast O(1) lookups
_LEVEL_TO_BAND: dict[BloomLevel, BloomBand] = {b.level: b for b in BLOOM_BANDS}


def get_band(level: BloomLevel) -> BloomBand:
    """Return the mastery band for a given Bloom level."""
    return _LEVEL_TO_BAND[level]


def get_level_from_mastery(mastery: float) -> BloomLevel:
    """
    Return the Bloom level that the mastery score falls into.
    Clamps out-of-range values to REMEMBER (below 0) or CREATE (above 100).
    """
    mastery = max(0.0, min(100.0, mastery))
    for band in BLOOM_BANDS:
        if mastery <= band.upper:
            return band.level
    return BloomLevel.CREATE


# ---------------------------------------------------------------------------
# Bloom weight multipliers used by the mastery updater.
# Higher cognitive levels carry a larger mastery delta per BKT unit.
# ---------------------------------------------------------------------------
BLOOM_WEIGHT: dict[BloomLevel, float] = {
    BloomLevel.REMEMBER:   1.0,
    BloomLevel.UNDERSTAND: 1.4,
    BloomLevel.APPLY:      1.8,
    BloomLevel.ANALYZE:    2.2,
    BloomLevel.EVALUATE:   2.6,
    BloomLevel.CREATE:     3.0,
}
