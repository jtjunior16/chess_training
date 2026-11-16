"""The game API, playing made-up bank positions inside a rolled-back transaction."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError, OperationalError

from chess_training import app as app_module
from chess_training.acceptance import AcceptanceSettings
from chess_training.app import GameConfig, app, get_conn, get_game_config
from chess_training.db import position_moves, position_sources, positions
from chess_training.game import GameSettings

VERSION = "test-app"
CFG = GameConfig(
    acceptance=AcceptanceSettings(G=5, L=6),
    game=GameSettings(position_choice="random", max_arrows=3),
    engine_version=VERSION,
)
MATE_FEN = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"  # White to move, Rd8 mates
OPENING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def add_position(conn, key, fen, moves, *, phase="opening", name=None):
    """moves: (uci, san, score_cp, score_mate). Only these moves get stored scores."""
    pid = conn.execute(
        insert(positions)
        .values(
            fen=fen,
            fen_key=key,  # made up, so it can't clash with a real bank position
            side_to_move=fen.split()[1],
            phase=phase,
            opening_name=name,
        )
        .returning(positions.c.id)
    ).scalar_one()
    conn.execute(
        insert(position_sources).values(
            position_id=pid,
            source="opening",
            source_ref=f"ref-{key}",
            fullmove_number=1,
            moves_to_position=[],
        )
    )
    for uci, san, score_cp, score_mate in moves:
        conn.execute(
            insert(position_moves).values(
                position_id=pid,
                uci=uci,
                san=san,
                score_cp=score_cp,
                score_mate=score_mate,
                depth=18,
                engine_version=VERSION,
            )
        )
    return pid


@pytest.fixture
def bank(conn):
    mate_id = add_position(
        conn,
        "app-test-mate",
        MATE_FEN,
        [("d1d8", "Rd8#", None, 1), ("h2h3", "h3", 0, None), ("g1f1", "Kf1", -10, None)],
        phase="endgame",
    )
    opening_id = add_position(
        conn,
        "app-test-opening",
        OPENING_FEN,
        [
            ("e2e4", "e4", 30, None),
            ("d2d4", "d4", 28, None),
            ("g1f3", "Nf3", 25, None),
            ("c2c4", "c4", 22, None),
            ("g2g4", "g4", -120, None),
        ],
        name="Test Opening",
    )
    # A checkmate: no legal moves, so analysis stores no scores and it must never be served.
    dead_id = add_position(
        conn, "app-test-dead", "3R2k1/5ppp/8/8/8/8/5PPP/6K1 b - - 1 1", [], phase="endgame"
    )
    return {"mate": mate_id, "opening": opening_id, "dead": dead_id}


@pytest.fixture
def client(conn, bank):
    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_game_config] = lambda: CFG
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_index_serves_the_board_page():
    res = TestClient(app).get("/")
    assert res.status_code == 200
    assert 'id="board"' in res.text and 'id="show-all"' in res.text


def test_position_by_id_includes_fen_dests_and_labels(client, bank):
    body = client.get("/api/position", params={"id": bank["opening"]}).json()
    assert body["id"] == bank["opening"]
    assert body["fen"] == OPENING_FEN
    assert body["turn"] == "white"
    assert body["phase"] == "opening" and body["opening"] == "Test Opening"
    assert "e4" in body["dests"]["e2"]


def test_random_position_is_a_playable_one(client, bank):
    # Only the made-up positions have scores for this test's engine version.
    served = {client.get("/api/position").json()["id"] for _ in range(20)}
    assert served <= {bank["mate"], bank["opening"]}


def test_position_without_scores_is_not_served(client, bank):
    res = client.get("/api/position", params={"id": bank["dead"]})
    assert res.status_code == 404
    assert client.get("/api/position", params={"id": 10**12}).status_code == 404


def test_best_move_in_an_only_move_position(client, bank):
    body = client.post(
        "/api/move", json={"position_id": bank["mate"], "move": "d1d8", "only_move": True}
    ).json()
    assert body["verdict"]["acceptable"] and body["verdict"]["text"] == "Acceptable (1st of 1)"
    assert body["count_text"] == "1 move was acceptable here"
    assert [m["san"] for m in body["arrows"]] == ["Rd8#"]
    assert body["second_best"]["san"] == "h3"
    assert body["second_best"]["label"] == "h3: misses the mate"
    assert body["only_move_claim"] is True


def test_acceptable_move_without_an_arrow(client, bank):
    body = client.post("/api/move", json={"position_id": bank["opening"], "move": "c2c4"}).json()
    assert body["verdict"]["text"] == "Acceptable (4th of 4)"
    assert [m["san"] for m in body["arrows"]] == ["e4", "d4", "Nf3"]
    assert len(body["acceptable"]) == 4
    assert body["second_best"] is None


def test_move_outside_the_set_is_not_acceptable(client, bank):
    body = client.post("/api/move", json={"position_id": bank["opening"], "move": "g2g4"}).json()
    assert not body["verdict"]["acceptable"]
    assert body["verdict"]["text"].startswith("Not acceptable (lost ")


def test_legal_move_without_a_stored_score_is_409(client, bank):
    # a2a3 is legal but this made-up position has no score for it (a real one always does).
    res = client.post("/api/move", json={"position_id": bank["opening"], "move": "a2a3"})
    assert res.status_code == 409


@pytest.mark.parametrize("move", ["d1d9", "e2e4", "zz"])
def test_bad_move_is_400(client, bank, move):
    res = client.post("/api/move", json={"position_id": bank["mate"], "move": move})
    assert res.status_code == 400


def test_move_in_unknown_position_is_404(client):
    res = client.post("/api/move", json={"position_id": 10**12, "move": "e2e4"})
    assert res.status_code == 404


def test_stats_endpoint_answers(client):
    assert client.get("/api/stats").status_code == 200


def test_unreachable_database_says_503_but_other_errors_stay_500():
    def down():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield  # a generator dependency, like get_conn

    def bug():
        raise IntegrityError("INSERT", {}, Exception("constraint"))
        yield

    try:
        app.dependency_overrides[get_conn] = down
        res = TestClient(app).get("/api/position")
        assert res.status_code == 503 and "OperationalError" in res.json()["detail"]
        app.dependency_overrides[get_conn] = bug
        res = TestClient(app, raise_server_exceptions=False).get("/api/position")
        assert res.status_code == 500
    finally:
        app.dependency_overrides.clear()


def test_without_a_database_the_api_says_503(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app_module._db.cache_clear()
    try:
        res = TestClient(app).get("/api/position")
        assert res.status_code == 503 and "DATABASE_URL" in res.json()["detail"]
    finally:
        app_module._db.cache_clear()
