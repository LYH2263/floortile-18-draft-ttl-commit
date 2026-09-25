from fastapi import APIRouter, Query

from app.schemas.estimate import ConfirmRequest, DraftRequest, EstimateRequest
from app.services import estimate_service

router = APIRouter(tags=["estimates"])


@router.get("/estimate")
def estimate_get(
    room_id: int = Query(...),
    tile_id: int = Query(...),
    waste_pct: float | None = None,
):
    return estimate_service.run_estimate(room_id, tile_id, waste_pct)


@router.post("/estimate")
def estimate_post(body: EstimateRequest):
    return estimate_service.run_estimate(body.room_id, body.tile_id, body.waste_pct)


@router.post("/estimate/draft")
def draft_post(body: DraftRequest):
    return estimate_service.create_draft(
        body.room_id, body.tile_id, body.waste_pct, body.note
    )


@router.post("/estimate/confirm")
def confirm_post(body: ConfirmRequest):
    return estimate_service.confirm_draft(body.draft_id)
