import pytest
from fastapi import HTTPException

import app.db as db
from app import seed
from app.repositories import drafts, history
from app.services import estimate_service


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    seed.init_db()


def run_count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    finally:
        conn.close()


def update_room(room_id: int, **fields):
    conn = db.connect()
    try:
        for col, val in fields.items():
            conn.execute(f"UPDATE rooms SET {col}=? WHERE id=?", (val, room_id))
        conn.commit()
    finally:
        conn.close()


def update_tile(tile_id: int, **fields):
    conn = db.connect()
    try:
        for col, val in fields.items():
            conn.execute(f"UPDATE tiles SET {col}=? WHERE id=?", (val, tile_id))
        conn.commit()
    finally:
        conn.close()


def test_draft_returns_id_expiry_and_counts_without_history(fresh_db):
    d = estimate_service.create_draft(1, 1, None)
    assert d["draft_id"]
    assert d["expires_at"]
    assert d["raw_count"] == 75
    assert d["order_count"] == 81
    assert run_count() == 0  # 草稿不落历史


def test_confirm_writes_one_run_matching_draft(fresh_db):
    d = estimate_service.create_draft(1, 1, None)
    r = estimate_service.confirm_draft(d["draft_id"])
    assert r["run_id"]
    assert r["raw_count"] == d["raw_count"]
    assert r["order_count"] == d["order_count"]
    assert run_count() == 1

    run = history.get_run(r["run_id"])
    assert run["result"]["raw_count"] == d["raw_count"]
    assert run["result"]["order_count"] == d["order_count"]
    assert drafts.get_draft(d["draft_id"])["status"] == "confirmed"


def test_duplicate_confirm_fails_and_keeps_history(fresh_db):
    d = estimate_service.create_draft(1, 1, None)
    estimate_service.confirm_draft(d["draft_id"])
    with pytest.raises(HTTPException) as ei:
        estimate_service.confirm_draft(d["draft_id"])
    assert ei.value.status_code == 409
    assert run_count() == 1


def test_expired_draft_fails_and_keeps_history(fresh_db):
    d = estimate_service.create_draft(1, 1, None, ttl_seconds=-1)
    with pytest.raises(HTTPException) as ei:
        estimate_service.confirm_draft(d["draft_id"])
    assert ei.value.status_code == 410
    assert run_count() == 0


def test_room_dims_changed_since_draft_fails(fresh_db):
    d = estimate_service.create_draft(1, 1, None)
    update_room(1, length=6.5)
    with pytest.raises(HTTPException) as ei:
        estimate_service.confirm_draft(d["draft_id"])
    assert ei.value.status_code == 409
    assert run_count() == 0


def test_tile_dims_changed_since_draft_fails(fresh_db):
    d = estimate_service.create_draft(1, 1, None)
    update_tile(1, tile_l=0.7)
    with pytest.raises(HTTPException) as ei:
        estimate_service.confirm_draft(d["draft_id"])
    assert ei.value.status_code == 409
    assert run_count() == 0


def test_confirm_unknown_draft_404(fresh_db):
    with pytest.raises(HTTPException) as ei:
        estimate_service.confirm_draft(9999)
    assert ei.value.status_code == 404
    assert run_count() == 0
