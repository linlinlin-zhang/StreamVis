from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


def build_streamvis_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "render_graph_delta",
                "description": "当用户需要可视化时，输出用于前端增量图渲染的 Graph Delta 操作列表。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ops": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "op": {"type": "string"},
                                    "id": {"type": "string"},
                                    "source": {"type": "string"},
                                    "target": {"type": "string"},
                                    "label": {"type": "string"},
                                    "value": {"type": "number"},
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                },
                                "required": ["op"],
                            },
                        }
                    },
                    "required": ["ops"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_image_prompt",
                "description": "当用户希望生成图片（例如信息图/海报/概念图）时，输出适合文生图模型的英文/中文 prompt。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "negative_prompt": {"type": "string"},
                    },
                    "required": ["prompt"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_image_edit",
                "description": "当用户希望编辑已有图片时，输出图像编辑任务参数。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function": {"type": "string"},
                        "prompt": {"type": "string"},
                        "base_image_url": {"type": "string"},
                        "n": {"type": "integer"},
                    },
                    "required": ["function", "prompt", "base_image_url"],
                },
            },
        },
    ]


def parse_tool_calls_from_chat_response(resp: Dict[str, Any]) -> Tuple[str, List[ToolCall]]:
    choices = resp.get("choices") or []
    if not choices:
        return "", []
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content") or ""
    raw_tool_calls = msg.get("tool_calls") or []
    calls: List[ToolCall] = []
    for tc in raw_tool_calls:
        if not isinstance(tc, dict):
            continue
        tc_id = str(tc.get("id") or "")
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
        except Exception:
            args = {}
        if tc_id and name:
            calls.append(ToolCall(id=tc_id, name=name, arguments=args))
    return str(content), calls


def get_raw_tool_calls(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    choices = resp.get("choices") or []
    if not choices:
        return []
    msg = (choices[0] or {}).get("message") or {}
    raw_tool_calls = msg.get("tool_calls") or []
    return raw_tool_calls if isinstance(raw_tool_calls, list) else []
