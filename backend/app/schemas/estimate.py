from pydantic import BaseModel


class EstimateRequest(BaseModel):
    room_id: int
    tile_id: int
    waste_pct: float | None = None


class DraftRequest(BaseModel):
    room_id: int
    tile_id: int
    waste_pct: float | None = None
    note: str = ""


class ConfirmRequest(BaseModel):
    draft_id: int


class EstimateResponse(BaseModel):
    room_id: int
    tile_id: int
    room_name: str
    tile_name: str
    area_m2: float
    piece_m2: float
    raw_count: int
    waste_pct: float
    order_count: int
    layout: dict


class DraftResponse(EstimateResponse):
    draft_id: int
    expires_at: str
    status: str


class ConfirmResponse(EstimateResponse):
    run_id: int
    draft_id: int
    confirmed_at: str
