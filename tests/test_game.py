"""The game's display logic (specs/move_acceptance_spec.md §8), on made-up scores (no database)."""

from __future__ import annotations

import random

import chess
import pytest

from chess_training.acceptance import AcceptanceSettings, ScoredMove, acceptable_set
from chess_training.game import (
    GameSettings,
    count_text,
    legal_dests,
    move_result,
    pick_position_id,
)

ACC = AcceptanceSettings(G=5, L=6)
GAME = GameSettings(position_choice="random", max_arrows=3)


def cp(uci, score):
    return ScoredMove(uci, uci.upper(), score, None)


def mate(uci, n):
    return ScoredMove(uci, uci.upper(), None, n)


# Five moves within a few win-% of each other, then a clear drop.
WIDE = [cp("a", 30), cp("b", 25), cp("c", 20), cp("d", 15), cp("e", 10), cp("bad", -300)]
# One move stands out: an only-move position.
ONLY = [cp("best", 300), cp("next", 0), cp("worse", -100)]


def test_config_values():
    assert GameSettings.from_config() == GAME


def test_unknown_position_choice_is_rejected():
    with pytest.raises(ValueError, match="position_choice"):
        GameSettings.from_config({"position_choice": "smart", "max_arrows": 3})


def test_arrows_are_capped_but_show_all_has_the_whole_set():
    r = move_result(acceptable_set(WIDE, ACC), "d", GAME)
    assert [m["uci"] for m in r["arrows"]] == ["a", "b", "c"]
    assert [m["uci"] for m in r["acceptable"]] == ["a", "b", "c", "d", "e"]
    # An acceptable move without an arrow is still acceptable: the verdict says so.
    assert r["verdict"]["acceptable"] and r["verdict"]["text"] == "Acceptable (4th of 5)"
    assert r["count_text"] == "5 moves were acceptable here"
    assert r["second_best"] is None


def test_arrows_never_point_at_a_move_that_isnt_acceptable():
    r = move_result(acceptable_set(WIDE, ACC), "bad", GAME)
    assert "bad" not in {m["uci"] for m in r["arrows"] + r["acceptable"]}
    assert not r["verdict"]["acceptable"]
    assert r["verdict"]["text"].startswith("Not acceptable (lost ")
    assert r["player"]["uci"] == "bad"


def test_only_move_position_shows_the_second_best_with_its_loss():
    r = move_result(acceptable_set(ONLY, ACC), "best", GAME)
    assert [m["uci"] for m in r["arrows"]] == ["best"]
    assert r["count_text"] == "1 move was acceptable here"
    s = r["second_best"]
    assert s["uci"] == "next"
    assert s["win_loss"] == pytest.approx(25.0, abs=1)  # +3.00 is about 75 win-%, 0.00 is 50
    assert s["label"] == f"NEXT: −{s['win_loss']:.1f} win-%"


def test_second_best_that_misses_a_mate_says_so():
    acc = acceptable_set([mate("m", 2), cp("big", 800), cp("small", 100)], ACC)
    s = move_result(acc, "big", GAME)["second_best"]
    assert s["uci"] == "big" and s["label"] == "BIG: misses the mate"


def test_two_mating_moves_are_not_an_only_move_position():
    acc = acceptable_set([mate("m1", 1), mate("m2", 3), cp("x", 900)], ACC)
    r = move_result(acc, "m2", GAME)
    assert r["second_best"] is None and r["verdict"]["acceptable"]


def test_a_position_with_one_legal_move_has_no_second_best():
    r = move_result(acceptable_set([cp("forced", 0)], ACC), "forced", GAME)
    assert r["second_best"] is None and r["count_text"] == "1 move was acceptable here"


def test_unscored_move_raises():
    with pytest.raises(ValueError):
        move_result(acceptable_set(WIDE, ACC), "zzz", GAME)


def test_count_text():
    assert count_text(1) == "1 move was acceptable here"
    assert count_text(12) == "12 moves were acceptable here"


def test_pick_is_from_the_given_ids_and_reproducible_with_a_seed():
    ids = [3, 7, 11]
    picks = [pick_position_id(ids, GAME, random.Random(1)) for _ in range(3)]
    assert len(set(picks)) == 1 and picks[0] in ids
    with pytest.raises(LookupError):
        pick_position_id([], GAME, random.Random(1))


def test_legal_dests_has_no_duplicate_targets():
    # A pawn on the 7th rank has 4 promotion moves to the same square.
    board = chess.Board("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    assert legal_dests(board)["a7"] == ["a8"]
