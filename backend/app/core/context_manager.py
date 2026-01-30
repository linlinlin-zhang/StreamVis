from __future__ import annotations

import uuid
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

from app.core.segmenter import StreamingSegmenter, extract_entities
from app.core.token_budget import budget_messages, estimate_tokens
from app.core.vector_store import InMemoryVectorStore, MemoryChunk

class ContextManager:
    def __init__(
        self,
        *,
        l1_max_turns: int = 14,
        sink_turns: int = 2,
        retrieval_k: int = 4,
        mmr_lambda: float = 0.65,
        mmr_pool_mult: int = 4,
        segmenter: Optional[StreamingSegmenter] = None,
        store: Optional[Any] = None,
    ) -> None:
        self._l1_max_turns = max(2, int(l1_max_turns))
        self._sink_turns = max(0, int(sink_turns))
        self._retrieval_k = max(0, int(retrieval_k))
        self._mmr_lambda = float(mmr_lambda)
        self._mmr_pool_mult = max(1, int(mmr_pool_mult))

        self._sink: List[Dict[str, Any]] = []
        self._system: List[Dict[str, Any]] = []
        self._recent: Deque[Dict[str, Any]] = deque()
        self._segmenter = segmenter or StreamingSegmenter()
        self._store = store or InMemoryVectorStore()
        self._owns_store = store is None
        self._entity_index: Dict[str, List[str]] = {}
        self._warm_entity_index()

    def clear(self, *, preserve_long_term: bool = True) -> None:
        self._sink.clear()
        self._system.clear()
        self._recent.clear()
        self._segmenter.flush()
        if not preserve_long_term and self._owns_store:
            self._store = InMemoryVectorStore()
            self._entity_index.clear()

    def add_user_input(self, text: str) -> None:
        self._append({"role": "user", "content": text})

    def add_assistant_output(self, text: str) -> None:
        self._append({"role": "assistant", "content": text})

    def add_system_context(self, text: str) -> None:
        t = (text or "").strip()
        if not t:
            return
        self._system.append({"role": "system", "content": t})
        while len(self._system) > 8:
            self._system.pop(0)

    def get_recent_context(self, k: int = 6) -> List[Dict[str, Any]]:
        if k <= 0:
            return []
        return list(self._recent)[-k:]

    def get_sink_context(self) -> List[Dict[str, Any]]:
        return list(self._sink)

    def get_augmented_context(self, query: str, *, max_prompt_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        k = self._effective_retrieval_k(query, max_prompt_tokens=max_prompt_tokens)
        retrieved = self.retrieve(query, k=k)
        mem_msgs: List[Dict[str, Any]] = []
        for ch in retrieved:
            mem_msgs.append({"role": "system", "content": f"[Memory:{ch.id}] {ch.text}"})
        msgs = self.get_sink_context() + list(self._system) + mem_msgs + list(self._recent)
        if max_prompt_tokens is None:
            return msgs
        budgeted, _ = budget_messages(msgs, max_prompt_tokens=max_prompt_tokens, keep_last_n=6, max_single_message_tokens=900)
        return budgeted

    def _effective_retrieval_k(self, query: str, *, max_prompt_tokens: Optional[int]) -> int:
        base = int(self._retrieval_k)
        if base <= 0:
            return 0
        qtok = estimate_tokens(query)
        if max_prompt_tokens is None:
            return base
        budget = int(max_prompt_tokens)
        if budget <= 0:
            return 0
        headroom = max(0, budget - qtok - 200)
        k_cap = max(0, min(base, headroom // 160))
        return max(0, k_cap)

    def retrieve(self, query: str, k: int = 4) -> List[MemoryChunk]:
        if k <= 0:
            return []
        hits: List[MemoryChunk] = []
        pool = max(k * self._mmr_pool_mult, k)

        ents = extract_entities(query)
        if ents:
            seen = set()
            for e in ents:
                for cid in self._entity_index.get(e, [])[:k]:
                    for ch in self._store.search(query, k=pool, mmr_lambda=self._mmr_lambda, candidate_pool=pool):
                        if ch.id == cid and ch.id not in seen:
                            hits.append(ch)
                            seen.add(ch.id)

        for ch in self._store.search(query, k=k, mmr_lambda=self._mmr_lambda, candidate_pool=pool):
            if ch not in hits:
                hits.append(ch)

        return hits[:k]

    def _warm_entity_index(self, *, max_chunks: int = 1200) -> None:
        try:
            chunks = list(self._store.iter_chunks())
        except Exception:
            return
        for ch in chunks[: max(0, int(max_chunks))]:
            meta = ch.meta or {}
            for e in meta.get("entities", []) or []:
                self._entity_index.setdefault(str(e), []).append(ch.id)

    def _append(self, msg: Dict[str, Any]) -> None:
        if len(self._sink) < self._sink_turns:
            self._sink.append(msg)
            return

        self._recent.append(msg)
        while len(self._recent) > self._l1_max_turns:
            evicted = self._recent.popleft()
            self._evict_to_long_term(evicted)

    def _evict_to_long_term(self, msg: Dict[str, Any]) -> None:
        content = (msg.get("content") or "").strip()
        if not content:
            return
        role = msg.get("role") or "unknown"
        segments = self._segmenter.add(content, meta={"role": role})
        for seg in segments:
            cid = seg.id or uuid.uuid4().hex[:12]
            self._store.add(cid, seg.text, meta=seg.meta)
            for e in seg.meta.get("entities", []) or []:
                self._entity_index.setdefault(str(e), []).insert(0, cid)

    def get_context_vector(self) -> List[float]:
        return [0.1, 0.2, 0.3]
