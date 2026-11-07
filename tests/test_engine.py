import chess
import pytest

from chess_training.engine import MATE_CP, Engine, Score
from chess_training.positions import BY_ID, SAMPLES


@pytest.fixture(scope="module")
def engine(require_stockfish):
    e = Engine()
    yield e
    e.close()


def test_samples_are_legal_positions():
    for p in SAMPLES:
        assert chess.Board(p.fen).is_valid(), p.id


def test_score_as_cp_ranks_mates_above_any_eval():
    assert Score(cp=None, mate=1).as_cp() > Score(cp=None, mate=3).as_cp() > 2000
    assert Score(cp=None, mate=-2).as_cp() == -(MATE_CP - 2)
    assert Score(cp=150, mate=None).as_cp() == 150


def test_finds_mate_in_one(engine):
    board = chess.Board(BY_ID["back-rank-mate"].fen)
    top = engine.top_moves(board)
    assert len(top) == 3
    assert top[0].san == "Rd8#"
    assert top[0].score.mate == 1


def test_only_move_position_has_a_big_gap(engine):
    board = chess.Board(BY_ID["blackburne-shilling-trap"].fen)
    top = engine.top_moves(board)
    assert top[0].san == "Qxg2"
    assert top[0].score.as_cp() - top[1].score.as_cp() > 300  # every other move is far worse


def test_score_move_scores_the_requested_move(engine):
    board = chess.Board(BY_ID["back-rank-mate"].fen)
    line = engine.score_move(board, chess.Move.from_uci("g1f1"))
    assert line.san == "Kf1"
    assert line.score.mate is None  # no longer mate after a quiet king move
