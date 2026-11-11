"""Engine score -> win percentage (specs/move_acceptance_spec.md §1).

The curve Lichess uses for accuracy: win% = 50 + 50 * (2 / (1 + e^(-0.00368208 * cp)) - 1).
Mates count as cp = +/-10,000, so their win% is about 100 or 0.
"""

from __future__ import annotations

import math

WIN_K = 0.00368208
MATE_AS_CP = 10_000


def win_pct_from_cp(cp: float) -> float:
    return 50 + 50 * (2 / (1 + math.exp(-WIN_K * cp)) - 1)


def win_pct(score_cp: int | None, score_mate: int | None) -> float:
    """Win % for the side the score is from. Exactly one of the two must be set."""
    if (score_cp is None) == (score_mate is None):
        raise ValueError("Exactly one of score_cp and score_mate must be set")
    if score_mate is not None:
        # Mate 0 is read as 'the side to move is already mated'. Careful: python-chess also
        # reports mate() == 0 for the winner's view of a finished mate (MateGiven). Batch
        # analysis stores neither, because positions with no legal moves are skipped.
        return win_pct_from_cp(MATE_AS_CP if score_mate > 0 else -MATE_AS_CP)
    return win_pct_from_cp(score_cp)
