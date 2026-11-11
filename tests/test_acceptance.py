"""Move acceptance (specs/move_acceptance_spec.md §2, §3, §4, §7) and its tuning report (§6)."""

from __future__ import annotations

import pytest
from sqlalchemy import insert

from chess_training.acceptance import (
    AcceptanceSettings,
    ScoredMove,
    acceptable_set,
    for_position,
    judge,
)
from chess_training.acceptance_report import load_bank, report, summarise
from chess_training.db import position_moves, position_sources, positions

S = AcceptanceSettings(G=5, L=6)


def cp(uci: str, score: int) -> ScoredMove:
    return ScoredMove(uci, uci, score, None)


def mate(uci: str, n: int) -> ScoredMove:
    return ScoredMove(uci, uci, None, n)


def test_settings_come_from_config():
    assert AcceptanceSettings.from_config() == AcceptanceSettings(G=5, L=6)


# ---------------------------------------------------------------- the spec's worked examples (§3)


def test_one_great_move_is_an_only_move_position():
    acc = acceptable_set([cp("best", 200)] + [cp(f"m{i}", 10) for i in range(20)], S)
    assert acc.size == 1 and acc.only_move
    assert acc.best.uci == "best"


def test_many_equal_moves_are_all_acceptable():
    moves = [cp(f"m{i:02d}", 20) for i in range(15)] + [cp("worse", -50)]
    acc = acceptable_set(moves, S)
    assert acc.size == 15
    assert "worse" not in {m.uci for m in acc.acceptable}


def test_slow_drift_is_stopped_by_the_cap():
    # +0.20, +0.15, +0.10, ... in 0.05 steps (about 0.5 win-% each): no break, so the cap
    # (best - 6 win-%) stops it at about -0.45.
    moves = [cp(f"m{i:02d}", 20 - 5 * i) for i in range(30)]
    acc = acceptable_set(moves, S)
    assert acc.acceptable[-1].score_cp == -45
    assert acc.size == 14


# ---------------------------------------------------------------- the rule (§2)


def test_break_stops_the_walk_even_if_later_moves_are_close():
    # 0 / -10 / then a break of more than G / then moves close to each other again
    moves = [cp("a", 0), cp("b", -10), cp("c", -300), cp("d", -305)]
    acc = acceptable_set(moves, S)
    assert [m.uci for m in acc.acceptable] == ["a", "b"]


def test_ranking_is_stable_for_equal_scores():
    moves = [cp("e2e4", 30), cp("d2d4", 30), cp("c2c4", 30)]
    assert [m.uci for m in acceptable_set(moves, S).ranked] == ["c2c4", "d2d4", "e2e4"]


def test_no_moves_is_an_error():
    with pytest.raises(ValueError):
        acceptable_set([], S)


# ---------------------------------------------------------------- forced mates (§7)


def test_any_forced_mate_is_acceptable_and_a_big_win_is_not():
    acc = acceptable_set([mate("m2", 2), mate("m9", 9), cp("plus8", 800), cp("ok", 300)], S)
    assert acc.forced_mate
    assert [m.uci for m in acc.acceptable] == ["m2", "m9"]  # sooner mate ranks first
    assert judge(acc, "plus8").acceptable is False


def test_one_mating_move_is_an_only_move_position():
    acc = acceptable_set([mate("mate", 1), cp("a", 900), cp("b", 850)], S)
    assert acc.only_move and acc.forced_mate


def test_two_mates_in_one_give_a_set_of_two():
    acc = acceptable_set([mate("x", 1), mate("y", 1), cp("z", 500)], S)
    assert acc.size == 2 and not acc.only_move


def test_losing_side_every_move_gets_mated_all_acceptable():
    acc = acceptable_set([mate("a", -1), mate("b", -3), mate("c", -5)], S)
    assert not acc.forced_mate
    assert acc.size == 3
    assert acc.best.uci == "c"  # being mated later is better


# ---------------------------------------------------------------- verdicts (§4, §8)


def test_verdict_for_an_acceptable_move():
    moves = [cp(f"m{i:02d}", 20) for i in range(12)] + [cp("bad", -200)]
    acc = acceptable_set(moves, S)
    v = judge(acc, "m06")
    assert v.acceptable and v.rank == 7 and v.acceptable_count == 12 and v.legal_count == 13
    assert v.text() == "Acceptable (7th of 12)"


def test_verdict_for_a_bad_move():
    acc = acceptable_set([cp("best", 0), cp("bad", -100)], S)
    v = judge(acc, "bad")
    assert not v.acceptable and v.only_move
    assert v.win_loss == pytest.approx(9.1, abs=0.1)
    assert v.text() == "Not acceptable (lost 9 win-%)"


@pytest.mark.parametrize(
    "n, text", [(1, "1st"), (2, "2nd"), (3, "3rd"), (11, "11th"), (22, "22nd")]
)
def test_ordinals(n, text):
    moves = [cp(f"m{i:02d}", 0) for i in range(25)]
    assert judge(acceptable_set(moves, AcceptanceSettings(G=5, L=100)), f"m{n - 1:02d}").text() == (
        f"Acceptable ({text} of 25)"
    )


def test_unknown_move_is_an_error():
    with pytest.raises(ValueError):
        judge(acceptable_set([cp("a", 0)], S), "zz")


# ---------------------------------------------------------------- database and report

VERSION = "test-acceptance"


def add_position(conn, key, phase, source, ref, moves, name=None):
    pid = conn.execute(
        insert(positions)
        .values(fen=key + " 0 30", fen_key=key, side_to_move="w", phase=phase, opening_name=name)
        .returning(positions.c.id)
    ).scalar_one()
    conn.execute(
        insert(position_sources).values(
            position_id=pid,
            source=source,
            source_ref=ref,
            fullmove_number=30,
            moves_to_position=["e4"],
        )
    )
    for m in moves:
        conn.execute(
            insert(position_moves).values(
                position_id=pid,
                uci=m.uci,
                san=m.san,
                score_cp=m.score_cp,
                score_mate=m.score_mate,
                depth=18,
                engine_version=VERSION,
            )
        )
    return pid


def test_for_position_reads_stored_scores(conn):
    pid = add_position(
        conn, "acc-test-1", "middlegame", "puzzle", "acc-p1", [cp("e2e4", 200), cp("d2d4", 10)]
    )
    acc = for_position(conn, pid, S, engine_version=VERSION)
    assert acc.only_move and acc.best.uci == "e2e4"


def test_report_runs_on_stored_positions(conn):
    add_position(
        conn, "acc-test-2", "endgame", "puzzle", "acc-p2", [mate("a1a8", 1), cp("a1a2", 300)]
    )
    add_position(
        conn,
        "acc-test-3",
        "opening",
        "opening",
        "acc-o3",
        [cp(f"m{i:02d}", 20) for i in range(6)] + [cp("bad", -400)],
        name="Test Opening",
    )
    bank = load_bank(conn, VERSION)
    assert {p.source for p in bank} == {"puzzle", "opening"}
    df, losses, _ = summarise(bank, S, blunder_line=15)
    assert sorted(df["size"]) == [1, 6]
    assert int(df["forced_mate"].sum()) == 1
    assert set(losses["kind"]) == {"blunder"}
    text = report(bank, S, 15, examples=1, total_positions=2)
    assert "Best move forces mate" in text and "Test Opening" in text
    assert "only-move share" in text
