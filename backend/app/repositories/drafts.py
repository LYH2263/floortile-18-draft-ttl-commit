import json
from datetime import datetime, timedelta, timezone

from app.db import connect


def insert_draft(
    room_id: int,
    tile_id: int,
    waste_pct: float,
    result: dict,
    snapshot: dict,
    note: str,
    ttl_seconds: float,
) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)
    conn = connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO estimate_drafts(
                room_id, tile_id, waste_pct, result_json, snapshot_json,
                note, status, created_at, expires_at
            )
            VALUES (?,?,?,?,?,?,'pending',?,?)
            """,
            (
                room_id,
                tile_id,
                waste_pct,
                json.dumps(result, ensure_ascii=False),
                json.dumps(snapshot, ensure_ascii=False),
                note,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
        return {"id": int(cur.lastrowid), "expires_at": expires_at.isoformat()}
    finally:
        conn.close()


def get_draft(draft_id: int):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM estimate_drafts WHERE id=?", (draft_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["result"] = json.loads(d.pop("result_json"))
        d["snapshot"] = json.loads(d.pop("snapshot_json"))
        return d
    finally:
        conn.close()


def confirm_draft_insert_run(draft_id: int, note: str = "") -> int | None:
    """Mark the draft confirmed and append its calc run in ONE transaction.

    The run row reuses the draft's stored result_json verbatim, so a
    successful confirm always implies exactly one matching history row.
    Returns the new run id, or None if the draft was not pending (already
    confirmed), in which case nothing is written.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        cur = conn.execute(
            """
            UPDATE estimate_drafts
            SET status='confirmed', confirmed_at=?
            WHERE id=? AND status='pending'
            """,
            (now, draft_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return None
        draft = conn.execute(
            """
            SELECT room_id, tile_id, waste_pct, result_json, note
            FROM estimate_drafts WHERE id=?
            """,
            (draft_id,),
        ).fetchone()
        cur = conn.execute(
            """
            INSERT INTO calc_runs(room_id, tile_id, waste_pct, result_json, note, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (
                draft["room_id"],
                draft["tile_id"],
                draft["waste_pct"],
                draft["result_json"],
                note or draft["note"],
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
