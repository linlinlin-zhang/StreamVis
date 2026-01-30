from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ChartPoint:
    x: str
    y: float


@dataclass(frozen=True)
class ChartSpec:
    chart_type: str
    title: str
    x_label: str
    y_label: str
    series_name: str
    points: List[ChartPoint]


_RE_DEFINE = re.compile(r"(?:定义|将)\s*([A-Za-z]\w*)\s*为\s*([^\n，。；;]+)")
_RE_ASSIGN_Q = re.compile(r"\b(Q[1-4])\b[^\n=]{0,12}=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)
_RE_ASSIGN_MONTH = re.compile(r"(?:(\d{1,2})\s*月)\s*[:：]?\s*(-?\d+(?:\.\d+)?)")
_RE_ASSIGN_X = re.compile(r"\b([A-Za-z]\w*)\s*=\s*(-?\d+(?:\.\d+)?)")


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


def parse_chart_spec(text: str) -> Optional[ChartSpec]:
    t = (text or "").strip()
    if not t:
        return None

    defines = _RE_DEFINE.findall(t)
    series_var = defines[-1][0] if defines else "Y"
    series_name = defines[-1][1].strip() if defines else "数值"

    points: List[ChartPoint] = []
    q_points = [(q.upper(), float(v)) for q, v in _RE_ASSIGN_Q.findall(t)]
    if q_points:
        order = ["Q1", "Q2", "Q3", "Q4"]
        order_index = {k: i for i, k in enumerate(order)}
        q_points.sort(key=lambda kv: order_index.get(kv[0], 9))
        points = [ChartPoint(x=q, y=v) for q, v in q_points]
        return ChartSpec(
            chart_type="line" if len(points) >= 3 else "bar",
            title=f"{series_name}季度趋势",
            x_label="季度",
            y_label=series_name,
            series_name=series_name,
            points=points,
        )

    m_points = [(int(m), float(v)) for m, v in _RE_ASSIGN_MONTH.findall(t)]
    if m_points:
        m_points.sort(key=lambda kv: kv[0])
        points = [ChartPoint(x=f"{m}月", y=v) for m, v in m_points]
        return ChartSpec(
            chart_type="line" if len(points) >= 3 else "bar",
            title=f"{series_name}月度趋势",
            x_label="月份",
            y_label=series_name,
            series_name=series_name,
            points=points,
        )

    var_points = [(k, float(v)) for k, v in _RE_ASSIGN_X.findall(t)]
    if var_points:
        pairs: List[Tuple[str, float]] = []
        for k, v in var_points:
            if k.lower() == series_var.lower() or k.lower() in {"x", "y"}:
                pairs.append((k, v))
        if pairs:
            points = [ChartPoint(x=f"点{i+1}", y=v) for i, (_, v) in enumerate(pairs)]
            return ChartSpec(
                chart_type="line" if len(points) >= 3 else "bar",
                title=f"{series_name}趋势",
                x_label="序号",
                y_label=series_name,
                series_name=series_name,
                points=points,
            )

    return None

