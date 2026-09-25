from fastapi import HTTPException

from app.engines.tile_math import tile_count
from app.repositories import drafts, rooms, settings_repo, tiles

_DRAFT_ERROR_STATUS = {
    "not_found": 404,
    "expired": 409,
    "already_confirmed": 409,
    "stale": 409,
}


def _load_room_tile(room_id: int, tile_id: int):
    room = rooms.get_room(room_id)
    if not room:
        raise HTTPException(404, "room not found")
    tile = tiles.get_tile(tile_id)
    if not tile:
        raise HTTPException(404, "tile not found")
    if room.get("data_quality") == "dirty":
        raise HTTPException(422, "room marked dirty; fix dimensions before estimate")
    return room, tile


def run_estimate(room_id: int, tile_id: int, waste_pct: float | None):
    """Pure preview: compute counts, persist nothing."""
    room, tile = _load_room_tile(room_id, tile_id)
    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()
    calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)
    return {
        "room_id": room_id,
        "tile_id": tile_id,
        "room": room,
        "tile": tile,
        **calc,
    }


def create_draft(room_id: int, tile_id: int, waste_pct: float | None, note: str = ""):
    """Phase 1: snapshot the estimate as a draft. History stays untouched."""
    room, tile = _load_room_tile(room_id, tile_id)
    waste = float(waste_pct) if waste_pct is not None else settings_repo.get_waste_pct()
    calc = tile_count(room["length"], room["width"], tile["tile_l"], tile["tile_w"], waste)
    draft = drafts.create_draft(room_id, tile_id, waste, room, tile, calc, note)
    return {
        "draft_id": draft["draft_id"],
        "expires_at": draft["expires_at"],
        "status": draft["status"],
        "room_id": room_id,
        "tile_id": tile_id,
        "room": room,
        "tile": tile,
        **calc,
    }


def confirm_draft(draft_id: int):
    """Phase 2: the only path that writes a history run."""
    try:
        confirmed = drafts.confirm_draft(draft_id)
    except drafts.DraftError as e:
        raise HTTPException(_DRAFT_ERROR_STATUS.get(e.code, 409), str(e)) from e
    return {
        "run_id": confirmed["run_id"],
        "draft_id": confirmed["draft_id"],
        "confirmed_at": confirmed["confirmed_at"],
        "room_id": confirmed["room_id"],
        "tile_id": confirmed["tile_id"],
        **confirmed["result"],
    }
