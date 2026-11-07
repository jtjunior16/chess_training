import pytest
from fastapi.testclient import TestClient

from chess_training.app import app
from chess_training.positions import BY_ID

MATE_FEN = BY_ID["back-rank-mate"].fen


@pytest.fixture(scope="module")
def client(require_stockfish):
    with TestClient(app) as c:  # `with` runs the lifespan, which starts Stockfish
        yield c


def test_index_serves_the_board_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert 'id="board"' in res.text


def test_position_includes_fen_and_legal_dests(client):
    res = client.get("/api/position", params={"id": "back-rank-mate"})
    assert res.status_code == 200
    body = res.json()
    assert body["fen"] == MATE_FEN
    assert body["turn"] == "white"
    assert "d8" in body["dests"]["d1"]


def test_unknown_position_id_is_404(client):
    assert client.get("/api/position", params={"id": "nope"}).status_code == 404


def test_best_move_loses_nothing(client):
    res = client.post("/api/move", json={"fen": MATE_FEN, "move": "d1d8", "only_move": True})
    assert res.status_code == 200
    body = res.json()
    assert body["in_top"] is True
    assert body["rank"] == 1
    assert body["loss_cp"] == 0
    assert body["only_move_claim"] is True


def test_worse_move_reports_a_loss(client):
    body = client.post("/api/move", json={"fen": MATE_FEN, "move": "h2h3"}).json()
    assert body["loss_cp"] > 0
    assert len(body["top"]) == 3


@pytest.mark.parametrize(
    ("fen", "move"),
    [(MATE_FEN, "d1d9"), (MATE_FEN, "e2e4"), ("not a fen", "e2e4")],
)
def test_bad_input_is_400(client, fen, move):
    assert client.post("/api/move", json={"fen": fen, "move": move}).status_code == 400
