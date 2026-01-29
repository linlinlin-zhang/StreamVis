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
    l1_max_turns: int
    sink_turns: int
    retrieval_k: int
    dashscope_api_key: str
    dashscope_workspace: str
    dashscope_base_url: str
    t2i_model: str
    t2i_size: str
    imageedit_model: str
    enable_images: bool
    moonshot_api_key: str
    moonshot_base_url: str
    moonshot_model: str
    enable_kimi: bool
    enable_kimi_tools: bool
    kimi_max_prompt_tokens: int
    waitk_chars: int
    graph_max_nodes: int
    graph_max_edges: int


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
        l1_max_turns=int(os.getenv("STREAMVIS_L1_MAX_TURNS", "14")),
        sink_turns=int(os.getenv("STREAMVIS_SINK_TURNS", "2")),
        retrieval_k=int(os.getenv("STREAMVIS_RETRIEVAL_K", "4")),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        dashscope_workspace=os.getenv("DASHSCOPE_WORKSPACE", ""),
        dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com"),
        t2i_model=os.getenv("STREAMVIS_T2I_MODEL", "wanx-v1"),
        t2i_size=os.getenv("STREAMVIS_T2I_SIZE", "1024*1024"),
        imageedit_model=os.getenv("STREAMVIS_IMAGEEDIT_MODEL", "wanx2.1-imageedit"),
        enable_images=os.getenv("STREAMVIS_ENABLE_IMAGES", "0").strip() in {"1", "true", "True"},
        moonshot_api_key=os.getenv("MOONSHOT_API_KEY", ""),
        moonshot_base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
        moonshot_model=os.getenv("STREAMVIS_KIMI_MODEL", "moonshot-v1-8k"),
        enable_kimi=os.getenv("STREAMVIS_ENABLE_KIMI", "0").strip() in {"1", "true", "True"},
        enable_kimi_tools=os.getenv("STREAMVIS_ENABLE_KIMI_TOOLS", "0").strip() in {"1", "true", "True"},
        kimi_max_prompt_tokens=int(os.getenv("STREAMVIS_KIMI_MAX_PROMPT_TOKENS", "5200")),
        waitk_chars=int(os.getenv("STREAMVIS_WAITK_CHARS", "120")),
        graph_max_nodes=int(os.getenv("STREAMVIS_GRAPH_MAX_NODES", "60")),
        graph_max_edges=int(os.getenv("STREAMVIS_GRAPH_MAX_EDGES", "120")),
    )
