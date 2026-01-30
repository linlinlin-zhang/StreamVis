from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.chart_parser import ChartSpec, parse_chart_spec


@dataclass(frozen=True)
class SemanticNode:
    id: str
    label: str
    value: float = 60.0


@dataclass(frozen=True)
class SemanticEdge:
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class SemanticPlan:
    chart_spec: Optional[ChartSpec]
    nodes: List[SemanticNode]
    edges: List[SemanticEdge]


_RE_CHART_TYPE = re.compile(r"(折线图|柱状图|饼图|散点图|趋势图)", re.IGNORECASE)


def build_semantic_plan(user_input: str) -> SemanticPlan:
    text = (user_input or "").strip()
    spec = parse_chart_spec(text)

    nodes: List[SemanticNode] = []
    edges: List[SemanticEdge] = []

    root_id = "req"
    nodes.append(SemanticNode(id=root_id, label="需求", value=86.0))

    chart_type = "图表"
    m = _RE_CHART_TYPE.search(text)
    if m:
        chart_type = m.group(1)
    if spec:
        chart_type = "折线图" if spec.chart_type == "line" else "柱状图"

    chart_id = f"chart:{chart_type}"
    nodes.append(SemanticNode(id=chart_id, label=chart_type, value=78.0))
    edges.append(SemanticEdge(source=root_id, target=chart_id, label="呈现"))

    if spec:
        metric_id = f"metric:{spec.y_label}"
        nodes.append(SemanticNode(id=metric_id, label=f"指标：{spec.y_label}", value=72.0))
        edges.append(SemanticEdge(source=chart_id, target=metric_id, label="度量"))

        x_id = f"dim:{spec.x_label}"
        nodes.append(SemanticNode(id=x_id, label=f"维度：{spec.x_label}", value=64.0))
        edges.append(SemanticEdge(source=chart_id, target=x_id, label="分组"))

        s_id = f"series:{spec.series_name}"
        nodes.append(SemanticNode(id=s_id, label=f"序列：{spec.series_name}", value=60.0))
        edges.append(SemanticEdge(source=chart_id, target=s_id, label="序列"))

        if spec.points:
            span = f"{spec.points[0].x} → {spec.points[-1].x}"
            data_id = "data:points"
            nodes.append(SemanticNode(id=data_id, label=f"数据点：{len(spec.points)}（{span}）", value=54.0))
            edges.append(SemanticEdge(source=metric_id, target=data_id, label="取值"))

    return SemanticPlan(chart_spec=spec, nodes=nodes, edges=edges)


def to_graph_ops(plan: SemanticPlan) -> List[Dict[str, Any]]:
    ops: List[Dict[str, Any]] = []
    for n in plan.nodes:
        ops.append({"op": "add_node", "id": n.id, "label": n.label, "value": float(n.value)})
    for e in plan.edges:
        ops.append({"op": "add_edge", "source": e.source, "target": e.target, "label": e.label})
    return ops

