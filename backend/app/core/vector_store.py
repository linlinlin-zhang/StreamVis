from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import time
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

def _mmr_select(
    candidates: List[Tuple[float, "MemoryChunk"]],
    *,
    k: int,
    lambda_mult: float,
) -> List["MemoryChunk"]:
    if k <= 0 or not candidates:
        return []
    lam = float(lambda_mult)
    lam = max(0.0, min(1.0, lam))

    selected: List[MemoryChunk] = []
    selected_embs: List[Tuple[float, ...]] = []

    while candidates and len(selected) < k:
        best_idx = -1
        best_score = -1e9
        for i, (sim_q, ch) in enumerate(candidates):
            if not selected_embs:
                score = sim_q
            else:
                max_sim = 0.0
                for emb in selected_embs:
                    s = _cosine(emb, ch.embedding)
                    if s > max_sim:
                        max_sim = s
                score = lam * sim_q - (1.0 - lam) * max_sim
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx < 0:
            break
        _, picked = candidates.pop(best_idx)
        selected.append(picked)
        selected_embs.append(picked.embedding)

    return selected


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

    def search(
        self,
        query: str,
        k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
        *,
        mmr_lambda: float = 0.0,
        candidate_pool: Optional[int] = None,
    ) -> List[MemoryChunk]:
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
        pool = int(candidate_pool or 0)
        if pool <= 0:
            pool = max(k * 4, 12)
        pool_scored = [(s, c) for s, c in scored[:pool] if s > 0.0]
        if mmr_lambda and mmr_lambda > 0.0:
            return _mmr_select(pool_scored, k=k, lambda_mult=mmr_lambda)
        return [c for s, c in pool_scored[:k]]

    def iter_chunks(self) -> Iterable[MemoryChunk]:
        return iter(self._chunks)


class PersistentVectorStore:
    def __init__(self, *, db_path: str, embedder: Optional[HashingEmbedder] = None) -> None:
        self._embedder = embedder or HashingEmbedder()
        self._db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                  id TEXT PRIMARY KEY,
                  text TEXT NOT NULL,
                  emb BLOB NOT NULL,
                  meta TEXT NOT NULL,
                  created_at INTEGER NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_created ON chunks(created_at);")
            conn.commit()
        finally:
            conn.close()

    def _pack_emb(self, emb: Sequence[float]) -> bytes:
        return struct.pack(f"<{len(emb)}f", *[float(v) for v in emb])

    def _unpack_emb(self, blob: bytes) -> Tuple[float, ...]:
        if not blob:
            return tuple()
        dim = len(blob) // 4
        return tuple(struct.unpack(f"<{dim}f", blob))

    def add(self, chunk_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        emb = self._embedder.embed(text)
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO chunks(id,text,emb,meta,created_at) VALUES (?,?,?,?,?)",
                (chunk_id, text, self._pack_emb(emb), meta_json, int(time.time())),
            )
            conn.commit()
        finally:
            conn.close()

    def search(
        self,
        query: str,
        k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
        *,
        mmr_lambda: float = 0.0,
        candidate_pool: Optional[int] = None,
    ) -> List[MemoryChunk]:
        if k <= 0:
            return []
        q = tuple(self._embedder.embed(query))
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id,text,emb,meta FROM chunks ORDER BY created_at DESC").fetchall()
        finally:
            conn.close()
        if not rows:
            return []
        scored: List[Tuple[float, MemoryChunk]] = []
        for cid, text, emb_blob, meta_json in rows:
            meta = {}
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {}
            if filters:
                ok = True
                for fk, fv in filters.items():
                    if meta.get(fk) != fv:
                        ok = False
                        break
                if not ok:
                    continue
            emb = self._unpack_emb(emb_blob)
            ch = MemoryChunk(id=str(cid), text=str(text), embedding=emb, meta=meta)
            scored.append((_cosine(q, emb), ch))
        scored.sort(key=lambda t: t[0], reverse=True)
        pool = int(candidate_pool or 0)
        if pool <= 0:
            pool = max(k * 4, 12)
        pool_scored = [(s, c) for s, c in scored[:pool] if s > 0.0]
        if mmr_lambda and mmr_lambda > 0.0:
            return _mmr_select(pool_scored, k=k, lambda_mult=mmr_lambda)
        return [c for s, c in pool_scored[:k]]

    def iter_chunks(self) -> Iterable[MemoryChunk]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id,text,emb,meta FROM chunks ORDER BY created_at DESC").fetchall()
        finally:
            conn.close()
        for cid, text, emb_blob, meta_json in rows:
            meta = {}
            try:
                meta = json.loads(meta_json) if meta_json else {}
            except Exception:
                meta = {}
            emb = self._unpack_emb(emb_blob)
            yield MemoryChunk(id=str(cid), text=str(text), embedding=emb, meta=meta)
