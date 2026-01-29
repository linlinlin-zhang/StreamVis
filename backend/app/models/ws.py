from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ClientMessage(BaseModel):
    type: Literal["user", "clear"] = "user"
    content: Optional[str] = None


class TextDeltaEvent(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    message_id: str
    content: str
    is_final: bool = True
    intent: Optional[Dict[str, Any]] = None


class GraphOp(BaseModel):
    op: str
    id: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    label: Optional[str] = None
    value: Optional[float] = None


class GraphDeltaEvent(BaseModel):
    type: Literal["graph_delta"] = "graph_delta"
    ops: List[GraphOp] = Field(default_factory=list)

