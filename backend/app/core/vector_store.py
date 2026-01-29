from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _l2_norm(vec: Sequence[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na = _l2_norm(a)
    nb = _l2_norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    dot = 0.0
    for x, y in zip(a, b):
        dot += x * y
    return dot / (na * nb)


class HashingEmbedder:
    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = -1.0 if (h[4] & 1) else 1.0
            vec[idx] += sign
        n = _l2_norm(vec)
        if n == 0.0:
            return vec
        return [v / n for v in vec]


@dataclass(frozen=True)
class MemoryChunk:
    id: str
    text: str
    embedding: Tuple[float, ...]
    meta: Dict[str, Any]


class InMemoryVectorStore:
    def __init__(self, embedder: Optional[HashingEmbedder] = None) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._chunks: List[MemoryChunk] = []

    def add(self, chunk_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        emb = tuple(self._embedder.embed(text))
        self._chunks.append(MemoryChunk(id=chunk_id, text=text, embedding=emb, meta=meta or {}))

    def search(self, query: str, k: int = 4, filters: Optional[Dict[str, Any]] = None) -> List[MemoryChunk]:
        if k <= 0 or not self._chunks:
            return []
        q = tuple(self._embedder.embed(query))

        scored: List[Tuple[float, MemoryChunk]] = []
        for ch in self._chunks:
            if filters:
                ok = True
                for fk, fv in filters.items():
                    if ch.meta.get(fk) != fv:
                        ok = False
                        break
                if not ok:
                    continue
            scored.append((_cosine(q, ch.embedding), ch))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for s, c in scored[:k] if s > 0.0]

    def iter_chunks(self) -> Iterable[MemoryChunk]:
        return iter(self._chunks)

