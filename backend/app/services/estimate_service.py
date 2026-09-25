from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import DRAFT_TTL_SECONDS
from app.engines.tile_math import tile_count
from app.repositories import drafts, rooms, settings_repo, tiles


def _load_room_tile(room_id: int, tile_id: int):
    room = rooms.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    tile = tiles.get_tile(tile_id)
    if not tile:
        raise HTTPException(404, "tile not found")
    return room, tile


def _snapshot(room: dict, tile: dict) -> dict:
    """Inputs that must stay unchanged between draft and confirm."""
    return {
        "room": {"length": room["length"], "width": room["width"]},
        "tile": {"tile_l": tile["tile_l"], "tile_w": tile["tile_w"]},
    }


def run_estimate(room_id: int, tile_id: int, waste_pct: float | None):
    room, tile = _load_room_tile(room_id, tile_id)
    if room.get("data_quality") == "dirty":
        raise HTTPException(422, "room marked dirty; fix dimensions before estimate")

    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()
    calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)

    return {
        "room_id": room_id,
        "tile_id": tile_id,
        "room": room,
        "tile": tile,
        **calc,
    }


def create_draft(
    room_id: int,
    tile_id: int,
    waste_pct: float | None,
    note: str = "",
    ttl_seconds: float = DRAFT_TTL_SECONDS,
):
    """Compute the estimate and persist it as a draft (no history row yet)."""
    room, tile = _load_room_tile(room_id, tile_id)
    if room.get("data_quality") == "dirty":
        raise HTTPException(422, "room marked dirty; fix dimensions before estimate")

    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()
    calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)
    draft = drafts.insert_draft(
        room_id, tile_id, waste, calc, _snapshot(room, tile), note, ttl_seconds
    )

    return {
        "draft_id": draft["id"],
        "expires_at": draft["expires_at"],
        "room_id": room_id,
        "tile_id": tile_id,
        "room": room,
        "tile": tile,
        **calc,
    }


def confirm_draft(draft_id: int, note: str = ""):
    """Write one calc run from a pending, unexpired, still-valid draft."""
    draft = drafts.get_draft(draft_id)
    if not draft:
        raise HTTPException(404, "draft not found")
    if draft["status"] != "pending":
        raise HTTPException(409, "draft already confirmed")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(draft["expires_at"]):
        raise HTTPException(410, "draft expired")

    room = rooms.get_room(draft["room_id"])
    tile = tiles.get_tile(draft["tile_id"])
    if not room or not tile or _snapshot(room, tile) != draft["snapshot"]:
        raise HTTPException(409, "room dimensions or tile changed since draft")

    run_id = drafts.confirm_draft_insert_run(draft_id, note or draft["note"])
    if run_id is None:
        raise HTTPException(409, "draft already confirmed")

    return {
        "run_id": run_id,
        "draft_id": draft_id,
        "room_id": draft["room_id"],
        "tile_id": draft["tile_id"],
        **draft["result"],
    }
