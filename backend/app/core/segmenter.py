from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.vector_store import HashingEmbedder


_ENTITY_RE = re.compile(r"\$?([A-Za-z][A-Za-z0-9_]{0,9})\$?")


def extract_entities(text: str) -> List[str]:
    t = text or ""
    out: List[str] = []
    for m in _ENTITY_RE.finditer(t):
        sym = (m.group(1) or "").strip()
        if not sym:
            continue
        if len(sym) == 1 and sym.isalpha() and sym.isupper():
            out.append(sym)
        elif sym.isidentifier() and len(sym) <= 10:
            out.append(sym)
    return sorted(set(out))


@dataclass
class Segment:
    id: str
    text: str
    meta: Dict[str, Any]


class StreamingSegmenter:
    def __init__(
        self,
        *,
        embedder: Optional[HashingEmbedder] = None,
        min_chars: int = 40,
        max_chars: int = 560,
        boundary_similarity: float = 0.35,
        max_turns: int = 4,
    ) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._min_chars = min_chars
        self._max_chars = max_chars
        self._boundary_similarity = boundary_similarity
        self._max_turns = max(2, int(max_turns))
        self._buf: List[str] = []
        self._buf_emb: Optional[Tuple[float, ...]] = None

    def _cosine(self, a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
        if na <= 0.0 or nb <= 0.0:
            return 0.0
        return dot / ((na**0.5) * (nb**0.5))

    def _buf_text(self) -> str:
        return "\n".join(s for s in self._buf if s)

    def add(self, text: str, meta: Optional[Dict[str, Any]] = None) -> List[Segment]:
        t = (text or "").strip()
        if not t:
            return []

        t_emb = tuple(self._embedder.embed(t))
        out: List[Segment] = []

        if self._buf:
            cur_text = self._buf_text()
            if len(cur_text) >= self._min_chars and self._buf_emb is not None:
                sim = self._cosine(self._buf_emb, t_emb)
                if sim < self._boundary_similarity:
                    out.extend(self.flush(meta=meta))

        self._buf.append(t)
        merged = self._buf_text()
        self._buf_emb = tuple(self._embedder.embed(merged))

        if len(merged) >= self._max_chars:
            out.extend(self.flush(meta=meta))

        if len(self._buf) >= self._max_turns and len(merged) >= max(40, self._min_chars // 2):
            out.extend(self.flush(meta=meta))

        if ("定义" in merged or "代表" in merged or "记为" in merged) and len(merged) >= 12:
            out.extend(self.flush(meta=meta))

        if merged and merged[-1] in "。！？!?":
            if len(merged) >= self._min_chars:
                out.extend(self.flush(meta=meta))

        return out

    def flush(self, meta: Optional[Dict[str, Any]] = None) -> List[Segment]:
        text = self._buf_text().strip()
        if not text:
            self._buf = []
            self._buf_emb = None
            return []

        seg_id = uuid.uuid4().hex[:12]
        merged_meta: Dict[str, Any] = {}
        if meta:
            merged_meta.update(meta)
        merged_meta["entities"] = extract_entities(text)
        seg = Segment(id=seg_id, text=text, meta=merged_meta)

        self._buf = []
        self._buf_emb = None
        return [seg]
