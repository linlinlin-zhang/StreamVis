from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ClientMessage(BaseModel):
    type: Literal["user", "system", "clear"] = "user"
    content: Optional[str] = None


class TextDeltaEvent(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    message_id: str
    content: str
    delta: Optional[str] = None
    is_final: bool = True
    intent: Optional[Dict[str, Any]] = None


class GraphOp(BaseModel):
    op: str
    id: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    label: Optional[str] = None
    value: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None


class GraphDeltaEvent(BaseModel):
    type: Literal["graph_delta"] = "graph_delta"
    ops: List[GraphOp] = Field(default_factory=list)


class ChartPoint(BaseModel):
    x: str
    y: float


class ChartDeltaEvent(BaseModel):
    type: Literal["chart_delta"] = "chart_delta"
    chart_type: Literal["line", "bar"] = "line"
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    series_name: str = ""
    points: List[ChartPoint] = Field(default_factory=list)


class ImageEvent(BaseModel):
    type: Literal["image"] = "image"
    request_id: str
    status: Literal["disabled", "queued", "running", "succeeded", "failed"]
    prompt: Optional[str] = None
    task_id: Optional[str] = None
    url: Optional[str] = None
    message: Optional[str] = None


class TranscriptDeltaEvent(BaseModel):
    type: Literal["transcript_delta"] = "transcript_delta"
    segment_id: str
    speaker: str
    text: str
    is_final: bool = False
