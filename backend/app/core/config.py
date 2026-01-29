from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    cors_origins: List[str]
    log_level: str
    visual_threshold: float


def _parse_origins(value: str | None) -> List[str]:
    if not value:
        return ["http://localhost:5173"]
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        host=os.getenv("STREAMVIS_HOST", "0.0.0.0"),
        port=int(os.getenv("STREAMVIS_PORT", "8000")),
        cors_origins=_parse_origins(os.getenv("STREAMVIS_CORS_ORIGINS")),
        log_level=os.getenv("STREAMVIS_LOG_LEVEL", "info"),
        visual_threshold=float(os.getenv("STREAMVIS_VISUAL_THRESHOLD", "0.55")),
    )

