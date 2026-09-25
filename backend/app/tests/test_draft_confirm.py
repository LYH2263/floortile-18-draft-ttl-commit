"""Draft -> confirm flow: only a successful confirm may add a history row."""

import os
import sqlite3
import tempfile

# config.py resolves DATA_DIR at import time; point it at a scratch dir first.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="floortile-test-"))

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    with TestClient(app) as c:
        c.db_path = db_path
        yield c


def run_count(client):
    return len(client.get("/api/runs").json()["items"])


def make_draft(client, room_id=1, tile_id=1):
    r = client.post("/api/estimate/draft", json={"room_id": room_id, "tile_id": tile_id})
    assert r.status_code == 200, r.text
    return r.json()


def exec_sql(client, sql, params=()):
    conn = sqlite3.connect(str(client.db_path))
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def test_draft_returns_snapshot_and_keeps_history(client):
    before = run_count(client)
    draft = make_draft(client)
    assert draft["draft_id"] > 0
    assert draft["status"] == "open"
    assert draft["expires_at"]
    # 当时 raw/order 随草稿一起返回
    assert draft["raw_count"] == 75
    assert draft["order_count"] == 81
    assert run_count(client) == before


def test_preview_does_not_persist_even_with_save_flag(client):
    r = client.get("/api/estimate?room_id=1&tile_id=1")
    assert r.status_code == 200
    r = client.post(
        "/api/estimate",
        json={"room_id": 1, "tile_id": 1, "save": True, "note": "old path"},
    )
    assert r.status_code == 200
    assert run_count(client) == 0


def test_confirm_writes_exactly_one_run(client):
    draft = make_draft(client)
    r = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run_id"] > 0
    assert body["draft_id"] == draft["draft_id"]

    assert run_count(client) == 1
    run = client.get(f"/api/runs/{body['run_id']}").json()
    # 历史行与草稿时的结果一致（确认不重算）
    assert run["result"]["raw_count"] == draft["raw_count"]
    assert run["result"]["order_count"] == draft["order_count"]
    assert run["room_name"] == "客餐厅"
    assert run["tile_name"] == "600x600"


def test_confirm_expired_draft_fails(client):
    draft = make_draft(client)
    exec_sql(
        client,
        "UPDATE estimate_drafts SET expires_at=? WHERE id=?",
        ("2000-01-01T00:00:00+00:00", draft["draft_id"]),
    )
    r = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert r.status_code == 409
    assert run_count(client) == 0


def test_confirm_twice_fails_and_keeps_single_run(client):
    draft = make_draft(client)
    first = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert first.status_code == 200
    second = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert second.status_code == 409
    assert run_count(client) == 1


def test_confirm_fails_when_room_dims_changed(client):
    draft = make_draft(client)
    exec_sql(client, "UPDATE rooms SET length=? WHERE id=?", (7.5, 1))
    r = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert r.status_code == 409
    assert run_count(client) == 0


def test_confirm_fails_when_tile_dims_changed(client):
    draft = make_draft(client)
    exec_sql(client, "UPDATE tiles SET tile_l=? WHERE id=?", (0.5, 1))
    r = client.post("/api/estimate/confirm", json={"draft_id": draft["draft_id"]})
    assert r.status_code == 409
    assert run_count(client) == 0


def test_confirm_unknown_draft_is_404(client):
    r = client.post("/api/estimate/confirm", json={"draft_id": 999999})
    assert r.status_code == 404
    assert run_count(client) == 0


def test_draft_rejects_dirty_room(client):
    r = client.post("/api/estimate/draft", json={"room_id": 3, "tile_id": 1})
    assert r.status_code == 422
    assert run_count(client) == 0
