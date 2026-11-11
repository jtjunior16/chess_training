"""Puzzle importer (specs/position_pipeline_spec.md §5), on synthetic data."""

from __future__ import annotations

from dataclasses import replace

import chess
import pandas as pd
import pytest
import zstandard
from sqlalchemy import func, select

from chess_training.config import load_config
from chess_training.db import position_sources, positions
from chess_training.fen import fen_key
from chess_training.puzzles import (
    COLUMNS,
    Sample,
    SampleSettings,
    draw_sample,
    even_band_targets,
    lichess_phase,
    quality_filter,
    read_chunks,
    training_position,
    write_sample,
)

START = chess.STARTING_FEN
# The board after 1.e4: the training position for a puzzle starting from the initial FEN.
AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def settings(**kw) -> SampleSettings:
    base = SampleSettings(
        min_nb_plays=100,
        min_popularity=80,
        sample_size=20,
        theme_floor=3,
        rating_band_width=200,
        seed=7,
        motif=frozenset({"fork", "pin", "smotheredMate"}),
        not_theme=frozenset({"middlegame", "short", "advantage"}),
        unplaced=frozenset({"kingsideAttack"}),
    )
    return replace(base, **kw)


def frame(n=200, **overrides) -> pd.DataFrame:
    """n puzzles spread over ratings 600-2599; every 10th is a fork, every 25th a pin."""
    rows = []
    for i in range(n):
        themes = ["middlegame", "short"]
        if i % 10 == 0:
            themes.append("fork")
        if i % 25 == 0:
            themes.append("pin")
        rows.append(
            {
                "PuzzleId": f"p{i:04d}",
                "FEN": START,
                "Moves": "e2e4 e7e5",
                "Rating": 600 + (i * 37) % 2000,
                "Popularity": 90,
                "NbPlays": 500,
                "Themes": " ".join(themes),
                "OpeningTags": pd.NA,
            }
        )
    df = pd.DataFrame(rows, columns=COLUMNS)
    for col, values in overrides.items():
        df[col] = values
    return df


def test_config_theme_lists_are_disjoint_and_cover_the_spec_examples():
    s = SampleSettings.from_config()
    assert not (s.motif & s.not_theme) and not (s.motif & s.unplaced)
    assert not (s.not_theme & s.unplaced)
    for tag in [
        "fork",
        "pin",
        "skewer",
        "intermezzo",
        "quietMove",
        "zugzwang",
        "xRayAttack",
        "backRankMate",
        "anastasiaMate",
        "mateIn1",
        "mateIn5",
    ]:
        assert tag in s.motif
    for tag in ["opening", "rookEndgame", "oneMove", "veryLong", "advantage", "mate", "superGM"]:
        assert tag in s.not_theme
    cfg = load_config()["puzzles"]
    assert (cfg["sample_size"], cfg["theme_floor"], cfg["rating_band_width"]) == (5000, 30, 200)
    assert (cfg["min_nb_plays"], cfg["min_popularity"]) == (100, 80)


def test_quality_filter_drops_rare_and_unpopular_puzzles():
    df = frame(4)
    df["NbPlays"] = [99, 100, 500, 500]
    df["Popularity"] = [90, 90, 79, 80]
    kept = quality_filter([df], settings())
    assert kept["PuzzleId"].tolist() == ["p0001", "p0003"]


def test_read_chunks_streams_zstd_csv(tmp_path):
    df = frame(5)
    raw = df.to_csv(index=False).encode()
    path = tmp_path / "p.csv.zst"
    path.write_bytes(zstandard.ZstdCompressor().compress(raw))
    back = pd.concat(read_chunks(path, chunksize=2), ignore_index=True)
    assert back["PuzzleId"].tolist() == df["PuzzleId"].tolist()


def test_training_position_is_after_the_opponents_first_move():
    board, san = training_position(START, "e2e4 e7e5 g1f3")
    assert san == "e4"
    assert fen_key(board) == fen_key(chess.Board(AFTER_E4))
    with pytest.raises(ValueError):
        training_position(START, "e2e5 e7e5")


def test_sample_meets_the_theme_floor_and_size():
    df = quality_filter([frame()], settings())
    sample = draw_sample(df, settings())
    assert len(sample.rows) == 20
    themes = " ".join(sample.rows["Themes"]).split()
    assert themes.count("fork") >= 3 and themes.count("pin") >= 3
    assert sample.short_themes == {"smotheredMate": 0}


def test_rare_theme_gets_everything_it_has():
    df = frame()
    df.loc[[5, 6], "Themes"] = "middlegame smotheredMate"
    sample = draw_sample(quality_filter([df], settings()), settings())
    assert sample.rows["Themes"].str.contains("smotheredMate").sum() == 2
    assert sample.short_themes == {"smotheredMate": 2}


def test_same_seed_same_sample_other_seed_other_sample():
    df = quality_filter([frame()], settings())
    a = draw_sample(df, settings()).rows
    b = draw_sample(df, settings()).rows
    c = draw_sample(df, settings(seed=8)).rows
    assert a["PuzzleId"].tolist() == b["PuzzleId"].tolist()
    assert a["PuzzleId"].tolist() != c["PuzzleId"].tolist()


def test_bands_end_up_even():
    df = quality_filter([frame(1000)], settings(sample_size=100, theme_floor=0))
    sample = draw_sample(df, settings(sample_size=100, theme_floor=0))
    per_band = (sample.rows["Rating"] // 200).value_counts()
    assert len(per_band) == 10 and set(per_band) == {10}


@pytest.mark.parametrize(
    "selected, available, total, expected",
    [
        # Floor picks sit in band 7: the others are topped up to match it first.
        ({7: 4}, {5: 10, 6: 10, 7: 10}, 12, {5: 4, 6: 4, 7: 0}),
        # Band 5 has only 1 puzzle: the others share its slots.
        ({}, {5: 1, 6: 10, 7: 10}, 9, {5: 1, 6: 4, 7: 4}),
        # Leftover slot goes to the lowest band first.
        ({}, {5: 10, 6: 10}, 3, {5: 2, 6: 1}),
        # Nothing to add when the floor already filled the sample.
        ({5: 3}, {5: 10}, 3, {5: 0}),
    ],
)
def test_even_band_targets(selected, available, total, expected):
    assert even_band_targets(selected, available, total) == expected


def test_floor_larger_than_sample_is_an_error():
    df = quality_filter([frame()], settings())
    with pytest.raises(ValueError, match="theme floor"):
        draw_sample(df, settings(sample_size=2))


def test_unknown_tags_are_reported():
    df = frame(10)
    df.loc[0, "Themes"] = "fork brandNewTag"
    sample = draw_sample(quality_filter([df], settings()), settings())
    assert dict(sample.unknown_tags) == {"brandNewTag": 1}


@pytest.mark.parametrize(
    "themes, expected",
    [("middlegame fork", "middlegame"), ("fork short", "none"), ("opening endgame", "several")],
)
def test_lichess_phase(themes, expected):
    assert lichess_phase(themes) == expected


def test_write_adds_sources_and_keeps_existing_positions(conn):
    rows = frame(3)
    # p0000 lands on the board after 1.e4, already in a filled bank or added here as an
    # "opening" row; p0001 and p0002 start from other boards.
    rows.loc[1, "Moves"] = "d2d4 d7d5"
    rows.loc[2, "Moves"] = "g1f3 d7d5"
    rows["OpeningTags"] = ["Kings_Pawn_Game", pd.NA, "Zukertort_Opening Zukertort_Opening_Other"]
    key = fen_key(chess.Board(AFTER_E4))
    existing = conn.execute(select(positions.c.id).where(positions.c.fen_key == key)).scalar()
    if existing is None:
        conn.execute(
            positions.insert().values(
                fen=AFTER_E4,
                fen_key=key,
                side_to_move="b",
                phase="opening",
                opening_name="King's Pawn Game",
                opening_names=["King's Pawn Game"],
            )
        )
    before = conn.execute(select(positions).where(positions.c.fen_key == key)).one()

    sample = Sample(rows=rows, candidates=3, short_themes={}, unknown_tags={})
    counts = write_sample(conn, sample)
    assert counts["sources"] == 3
    assert conn.execute(select(positions).where(positions.c.fen_key == key)).one() == before

    src = conn.execute(
        select(position_sources).where(position_sources.c.source_ref == "p0002")
    ).one()
    assert src.source == "puzzle"
    assert src.moves_to_position == ["Nf3"]
    assert src.puzzle_opening_tags == ["Zukertort_Opening", "Zukertort_Opening_Other"]
    assert src.puzzle_themes == ["middlegame", "short"]
    assert src.puzzle_rating == 600 + 74

    n_positions = conn.execute(select(func.count()).select_from(positions)).scalar_one()
    again = write_sample(conn, sample)  # second run: same rows, nothing new
    assert again["new_positions"] == 0
    assert conn.execute(select(func.count()).select_from(positions)).scalar_one() == n_positions
    n = conn.execute(
        select(position_sources.c.id).where(
            position_sources.c.source_ref.in_(["p0000", "p0001", "p0002"])
        )
    ).all()
    assert len(n) == 3


def test_new_puzzle_board_is_not_an_opening_by_naming(conn):
    # A middlegame-ish board at move 30: phase comes from the rule without the named-line test.
    fen = "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R2QKB1R w KQ - 0 30"
    rows = frame(1)
    rows["FEN"] = [fen]
    rows["Moves"] = ["a2a3 a7a6"]
    sample = Sample(rows=rows, candidates=1, short_themes={}, unknown_tags={})
    write_sample(conn, sample)
    board = chess.Board(fen)
    board.push_uci("a2a3")
    phase = conn.execute(
        select(positions.c.phase).where(positions.c.fen_key == fen_key(board))
    ).scalar_one()
    assert phase == "middlegame"
