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
    enable_persistent_memory: bool
    memory_db_path: str
    mmr_lambda: float
    mmr_pool_mult: int
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
    waitk_min_interval_ms: int
    waitk_max_updates: int
    graph_max_nodes: int
    graph_max_edges: int
    enable_context_summary: bool
    system_context_max_chars: int
    system_context_summary_chars: int
    xfyun_enable: bool
    xfyun_app_id: str
    xfyun_access_key_id: str
    xfyun_access_key_secret: str
    xfyun_rtasr_base_url: str
    xfyun_lang: str
    xfyun_audio_encode: str
    xfyun_samplerate: int
    xfyun_role_type: int
    xfyun_feature_ids: str
    xfyun_eng_spk_match: int
    xfyun_voiceprint_register_url: str
    xfyun_voiceprint_update_url: str
    xfyun_voiceprint_delete_url: str


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
        enable_persistent_memory=os.getenv("STREAMVIS_ENABLE_PERSISTENT_MEMORY", "1").strip() in {"1", "true", "True"},
        memory_db_path=os.getenv("STREAMVIS_MEMORY_DB_PATH", "data/streamvis_memory.sqlite"),
        mmr_lambda=float(os.getenv("STREAMVIS_MMR_LAMBDA", "0.65")),
        mmr_pool_mult=int(os.getenv("STREAMVIS_MMR_POOL_MULT", "4")),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        dashscope_workspace=os.getenv("DASHSCOPE_WORKSPACE", ""),
        dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com"),
        t2i_model=os.getenv("STREAMVIS_T2I_MODEL", "qwen-image-max"),
        t2i_size=os.getenv("STREAMVIS_T2I_SIZE", "1024*1024"),
        imageedit_model=os.getenv("STREAMVIS_IMAGEEDIT_MODEL", "qwen-image-edit-max"),
        enable_images=os.getenv("STREAMVIS_ENABLE_IMAGES", "0").strip() in {"1", "true", "True"},
        moonshot_api_key=os.getenv("MOONSHOT_API_KEY", ""),
        moonshot_base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
        moonshot_model=os.getenv("STREAMVIS_KIMI_MODEL", "kimi-k2.5"),
        enable_kimi=os.getenv("STREAMVIS_ENABLE_KIMI", "0").strip() in {"1", "true", "True"},
        enable_kimi_tools=os.getenv("STREAMVIS_ENABLE_KIMI_TOOLS", "0").strip() in {"1", "true", "True"},
        kimi_max_prompt_tokens=int(os.getenv("STREAMVIS_KIMI_MAX_PROMPT_TOKENS", "5200")),
        waitk_chars=int(os.getenv("STREAMVIS_WAITK_CHARS", "120")),
        waitk_min_interval_ms=int(os.getenv("STREAMVIS_WAITK_MIN_INTERVAL_MS", "700")),
        waitk_max_updates=int(os.getenv("STREAMVIS_WAITK_MAX_UPDATES", "4")),
        graph_max_nodes=int(os.getenv("STREAMVIS_GRAPH_MAX_NODES", "60")),
        graph_max_edges=int(os.getenv("STREAMVIS_GRAPH_MAX_EDGES", "120")),
        enable_context_summary=os.getenv("STREAMVIS_ENABLE_CONTEXT_SUMMARY", "0").strip() in {"1", "true", "True"},
        system_context_max_chars=int(os.getenv("STREAMVIS_SYSTEM_CONTEXT_MAX_CHARS", "8000")),
        system_context_summary_chars=int(os.getenv("STREAMVIS_SYSTEM_CONTEXT_SUMMARY_CHARS", "900")),
        xfyun_enable=os.getenv("STREAMVIS_ENABLE_XFYUN_ASR", "0").strip() in {"1", "true", "True"},
        xfyun_app_id=os.getenv("XFYUN_APP_ID", ""),
        xfyun_access_key_id=os.getenv("XFYUN_ACCESS_KEY_ID", ""),
        xfyun_access_key_secret=os.getenv("XFYUN_ACCESS_KEY_SECRET", ""),
        xfyun_rtasr_base_url=os.getenv("XFYUN_RTASR_BASE_URL", "wss://office-api-ast-dx.iflyaisol.com/ast/communicate/v1"),
        xfyun_lang=os.getenv("XFYUN_LANG", "autodialect"),
        xfyun_audio_encode=os.getenv("XFYUN_AUDIO_ENCODE", "pcm_s16le"),
        xfyun_samplerate=int(os.getenv("XFYUN_SAMPLERATE", "16000")),
        xfyun_role_type=int(os.getenv("XFYUN_ROLE_TYPE", "2")),
        xfyun_feature_ids=os.getenv("XFYUN_FEATURE_IDS", ""),
        xfyun_eng_spk_match=int(os.getenv("XFYUN_ENG_SPK_MATCH", "0")),
        xfyun_voiceprint_register_url=os.getenv("XFYUN_VOICEPRINT_REGISTER_URL", ""),
        xfyun_voiceprint_update_url=os.getenv("XFYUN_VOICEPRINT_UPDATE_URL", ""),
        xfyun_voiceprint_delete_url=os.getenv("XFYUN_VOICEPRINT_DELETE_URL", ""),
    )
