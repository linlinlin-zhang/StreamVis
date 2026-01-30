from __future__ import annotations

from typing import Optional

from app.core.kimi_client import KimiClient, KimiError


def summarize_system_context(
    kimi_client: Optional[KimiClient],
    text: str,
    *,
    target_chars: int = 900,
) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if target_chars <= 0:
        return ""
    if len(t) <= target_chars:
        return t
    if not kimi_client:
        return t[:target_chars]

    prompt = (
        "请将下面的材料压缩成一段“系统上下文摘要”，要求：\n"
        f"- 不超过 {target_chars} 个中文字符左右\n"
        "- 保留关键实体（指标、时间范围、单位、口径、约束）\n"
        "- 不要编造数据\n"
        "- 输出纯文本，不要列表编号\n\n"
        "材料：\n"
        + t
    )
    try:
        resp = kimi_client.chat(
            messages=[{"role": "system", "content": "你是严格的摘要器。"}, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=900,
            stream=False,
        )
        choices = resp.get("choices") or []
        msg = (choices[0] or {}).get("message") if choices else {}
        out = (msg or {}).get("content") or ""
        out = str(out).strip()
        if not out:
            return t[:target_chars]
        if len(out) > target_chars * 2:
            return out[:target_chars]
        return out
    except KimiError:
        return t[:target_chars]

