import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

DEFAULT_WASTE_PCT = 8.0

# 草稿有效期（分钟），确认接口只接受未过期的草稿
DRAFT_TTL_MINUTES = float(os.environ.get("DRAFT_TTL_MINUTES", "15"))
