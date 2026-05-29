from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_name: str = "GeriCare"
    facility_name: str = os.getenv("GERICARE_FACILITY_NAME", "Residencial Aurora")
    database_path: str = os.getenv("GERICARE_DB", str(BASE_DIR / "data" / "gericare.sqlite3"))
    auto_seed: bool = os.getenv("GERICARE_AUTO_SEED", "1").lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
