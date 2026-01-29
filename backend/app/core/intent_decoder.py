from __future__ import annotations

from typing import Any, Dict, List


class IntentDecoder:
    def detect(self, text: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        t = (text or "").strip().lower()
        if not t:
            return {"type": "inform", "visual_necessity_score": 0.0, "entities": []}

        strong_triggers = [
            "画图",
            "画个图",
            "可视化",
            "绘制",
            "折线图",
            "柱状图",
            "饼图",
            "散点图",
            "趋势图",
            "chart",
            "plot",
            "graph",
            "visualize",
        ]
        weak_triggers = [
            "趋势",
            "对比",
            "变化",
            "波动",
            "分布",
            "增长",
            "下降",
            "同比",
            "环比",
            "show",
            "trend",
            "compare",
        ]

        score = 0.05
        if any(s in t for s in strong_triggers):
            score += 0.7
        if any(s in t for s in weak_triggers):
            score += 0.25
        if any(ch.isdigit() for ch in t):
            score += 0.08

        score = max(0.0, min(1.0, score))
        intent_type = "request-create" if score >= 0.55 else "inform"
        return {"type": intent_type, "visual_necessity_score": score, "entities": []}
