from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.segmenter import StreamingSegmenter


_RE_SPLIT = re.compile(r"\n{2,}")


def _chunks_from_text(text: str) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    parts = _RE_SPLIT.split(t)
    out: List[str] = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        out.append(s)
    return out


def index_text(
    *,
    store: Any,
    text: str,
    meta: Optional[Dict[str, Any]] = None,
    segmenter: Optional[StreamingSegmenter] = None,
) -> Tuple[int, List[str]]:
    seg = segmenter or StreamingSegmenter(min_chars=80, max_chars=760, boundary_similarity=0.25, max_turns=12)
    ids: List[str] = []
    count = 0
    for part in _chunks_from_text(text):
        for s in seg.add(part, meta=meta):
            cid = s.id or uuid.uuid4().hex[:12]
            store.add(cid, s.text, meta=s.meta)
            ids.append(cid)
            count += 1
    for s in seg.flush(meta=meta):
        cid = s.id or uuid.uuid4().hex[:12]
        store.add(cid, s.text, meta=s.meta)
        ids.append(cid)
        count += 1
    return count, ids

