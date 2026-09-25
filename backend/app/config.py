import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

DEFAULT_WASTE_PCT = 8.0

# 草稿有效期：超过该时长后确认接口拒绝写历史
DRAFT_TTL_SECONDS = 300
