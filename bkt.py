"""
bkt.py
------
Standard Bayesian Knowledge Tracing (BKT) model.

BKT models a student's latent knowledge of a skill as a hidden binary variable:
    L_n ∈ {not learned, learned}

Four parameters govern the model (all in [0, 1]):
    P(L₀)  Prior probability of already knowing the skill.
    P(T)   Learning rate — probability of transitioning from not-learned to
           learned after a practice opportunity.
    P(S)   Slip probability — probability of answering incorrectly despite knowing.
    P(G)   Guess probability — probability of answering correctly without knowing.

Update equations (standard BKT):
    Step 1 — Bayesian posterior given evidence:
        P(Lₙ | correct)  = P(Lₙ)(1 − P(S))
                           ─────────────────────────────────────────
                           P(Lₙ)(1 − P(S)) + (1 − P(Lₙ)) · P(G)

        P(Lₙ | incorrect) = P(Lₙ) · P(S)
                            ─────────────────────────────────────────
                            P(Lₙ) · P(S) + (1 − P(Lₙ)) · (1 − P(G))

    Step 2 — Learning transition:
        P(Lₙ₊₁) = P(Lₙ | evidence) + (1 − P(Lₙ | evidence)) · P(T)

This class is intentionally stateless — it only computes updated probabilities.
State (P(Lₙ) per skill per student) is owned by StudentModel.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Parameter container
# ---------------------------------------------------------------------------
@dataclass
class BKTParams:
    """
    Hyperparameters for a single BKT skill model.

    Attributes
    ----------
    p_l0  : Prior P(learned) before any observations.
    p_t   : Learning rate P(transit).
    p_s   : Slip probability P(slip).
    p_g   : Guess probability P(guess).
    """
    p_l0: float = 0.30
    p_t:  float = 0.10
    p_s:  float = 0.10
    p_g:  float = 0.20

    def __post_init__(self) -> None:
        for attr, val in (
            ("p_l0", self.p_l0),
            ("p_t",  self.p_t),
            ("p_s",  self.p_s),
            ("p_g",  self.p_g),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"BKTParams.{attr} must be in [0, 1], got {val}.")

    # Convenience constructors for common configurations
    @classmethod
    def default(cls) -> BKTParams:
        """Conservative defaults suitable for most skills."""
        return cls(p_l0=0.30, p_t=0.10, p_s=0.10, p_g=0.20)

    @classmethod
    def fast_learner(cls) -> BKTParams:
        """Higher learning rate for simple prerequisite skills."""
        return cls(p_l0=0.40, p_t=0.20, p_s=0.05, p_g=0.15)

    @classmethod
    def slow_learner(cls) -> BKTParams:
        """Lower learning rate for complex derived skills."""
        return cls(p_l0=0.10, p_t=0.05, p_s=0.15, p_g=0.25)


# ---------------------------------------------------------------------------
# BKT model (stateless)
# ---------------------------------------------------------------------------
class BKTModel:
    """
    A stateless BKT engine.  Given the current P(learned) and an observation,
    it returns the updated P(learned).

    Being stateless makes this model trivially replaceable with a more advanced
    variant (e.g. individualised BKT, deep knowledge tracing) without altering
    any call sites — only StudentModel.get_p_learned / set_p_learned change.
    """

    def __init__(self, params: BKTParams | None = None) -> None:
        self.params = params or BKTParams.default()

    # --------------------------------------------------------------- core API
    def update(self, p_ln: float, is_correct: bool) -> float:
        """
        Compute P(Lₙ₊₁) given the current P(Lₙ) and an observation.

        Parameters
        ----------
        p_ln        : Current probability of having learned the skill P(Lₙ).
        is_correct  : True if the student answered correctly.

        Returns
        -------
        Updated probability P(Lₙ₊₁) clamped to [0, 1].
        """
        p_l = p_ln
        p_t = self.params.p_t
        p_s = self.params.p_s
        p_g = self.params.p_g

        # --- Step 1: Bayesian posterior -----------------------------------
        if is_correct:
            numerator   = p_l * (1.0 - p_s)
            denominator = numerator + (1.0 - p_l) * p_g
        else:
            numerator   = p_l * p_s
            denominator = numerator + (1.0 - p_l) * (1.0 - p_g)

        # Guard against degenerate denominator (shouldn't happen with valid params)
        if denominator < 1e-12:
            p_l_given_evidence = p_l
        else:
            p_l_given_evidence = numerator / denominator

        # --- Step 2: Learning transition ----------------------------------
        p_ln_plus_1 = p_l_given_evidence + (1.0 - p_l_given_evidence) * p_t

        return float(max(0.0, min(1.0, p_ln_plus_1)))

    def predict_correct(self, p_ln: float) -> float:
        """
        Compute the predicted probability of a correct answer given P(Lₙ).
        Useful for question selection (pick questions where expected accuracy
        is near 0.7 for optimal challenge).

        P(correct) = P(Lₙ)(1 − P(S)) + (1 − P(Lₙ)) · P(G)
        """
        return p_ln * (1.0 - self.params.p_s) + (1.0 - p_ln) * self.params.p_g

    # --------------------------------------------------------------- dunder
    def __repr__(self) -> str:
        p = self.params
        return (
            f"BKTModel(p_l0={p.p_l0}, p_t={p.p_t}, "
            f"p_s={p.p_s}, p_g={p.p_g})"
        )
