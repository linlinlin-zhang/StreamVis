from __future__ import annotations

from typing import Any, Dict, List, Tuple


def estimate_tokens(text: str) -> int:
    s = text or ""
    if not s:
        return 0
    ascii_count = 0
    non_ascii_count = 0
    for ch in s:
        if ord(ch) < 128:
            ascii_count += 1
        else:
            non_ascii_count += 1
    return max(1, int(ascii_count / 4.0 + non_ascii_count / 1.5))


def estimate_message_tokens(msg: Dict[str, Any]) -> int:
    role = str(msg.get("role") or "")
    content = msg.get("content")
    if isinstance(content, list):
        joined = ""
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                joined += str(part["text"])
        content = joined
    return estimate_tokens(f"{role}:{content}")


def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    s = text or ""
    if estimate_tokens(s) <= max_tokens:
        return s
    limit_chars = max(24, int(max_tokens * 3.2))
    return s[:limit_chars]


def budget_messages(
    msgs: List[Dict[str, Any]],
    *,
    max_prompt_tokens: int,
    keep_last_n: int = 4,
    max_single_message_tokens: int = 900,
) -> Tuple[List[Dict[str, Any]], int]:
    if max_prompt_tokens <= 0:
        return [], 0

    trimmed: List[Dict[str, Any]] = []
    for m in msgs:
        mm = dict(m)
        content = mm.get("content")
        if isinstance(content, str):
            if estimate_tokens(content) > max_single_message_tokens:
                mm["content"] = truncate_text_to_tokens(content, max_single_message_tokens)
        trimmed.append(mm)

    if not trimmed:
        return [], 0

    kept_tail = trimmed[-keep_last_n:] if keep_last_n > 0 else []
    head = trimmed[: max(0, len(trimmed) - len(kept_tail))]

    total = sum(estimate_message_tokens(m) for m in kept_tail)
    out: List[Dict[str, Any]] = list(kept_tail)

    for m in reversed(head):
        t = estimate_message_tokens(m)
        if total + t > max_prompt_tokens:
            continue
        out.insert(0, m)
        total += t

    return out, total

