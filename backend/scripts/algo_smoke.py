from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.context_manager import ContextManager
from app.core.chart_parser import parse_chart_spec
from app.core.kimi_tools import get_raw_tool_calls, parse_tool_calls_from_chat_response
from app.core.renderer import IncrementalRenderer
from app.core.token_budget import budget_messages, estimate_tokens
from app.core.vector_store import PersistentVectorStore
from app.core.waitk_policy import WaitKPolicy


def main() -> None:
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("中文测试") > 0

    msgs = [{"role": "system", "content": "a" * 5000}, {"role": "user", "content": "hi"}]
    kept, total = budget_messages(msgs, max_prompt_tokens=100, keep_last_n=1, max_single_message_tokens=50)
    assert kept[-1]["role"] == "user"
    assert total <= 100

    cm = ContextManager(l1_max_turns=4, sink_turns=1, retrieval_k=4)
    cm.add_user_input("第1轮：一些背景信息 " * 20)
    cm.add_assistant_output("好的 " * 30)
    cm.add_user_input("第2轮：更多背景 " * 20)
    cm.add_assistant_output("继续 " * 30)
    cm.add_user_input("第3轮：更多背景 " * 20)
    ctx = cm.get_augmented_context("请总结", max_prompt_tokens=200)
    assert isinstance(ctx, list)
    assert len(ctx) > 0

    r = IncrementalRenderer(max_nodes=3, max_edges=3)
    for _ in range(8):
        r.generate_delta({}, [])
    assert len(r.nodes) <= 3
    assert len(r.edges) <= 3

    spec = parse_chart_spec("请画个图。定义X为净利润。Q1 X=120，Q2 X=130，Q3 X=90")
    assert spec is not None
    assert spec.y_label == "净利润"
    assert len(spec.points) == 3

    fake_resp = {
        "choices": [
            {
                "message": {
                    "content": "ok",
                    "tool_calls": [
                        {
                            "id": "tc_1",
                            "type": "function",
                            "function": {"name": "render_graph_delta", "arguments": "{\"ops\": []}"},
                        }
                    ],
                }
            }
        ]
    }
    content, calls = parse_tool_calls_from_chat_response(fake_resp)
    assert content == "ok"
    assert calls and calls[0].name == "render_graph_delta"
    raw = get_raw_tool_calls(fake_resp)
    assert raw and raw[0]["id"] == "tc_1"

    p = WaitKPolicy(step_chars=10, min_interval_ms=100, max_updates=2)
    assert p.observe(delta="12345", now_ms=0) is False
    assert p.observe(delta="67890", now_ms=0) is True
    assert p.observe(delta="abcde", now_ms=50) is False
    assert p.observe(delta="fghij", now_ms=120) is True
    assert p.observe(delta="klmno", now_ms=300) is False

    db_path = os.path.join(os.path.dirname(__file__), "tmp_memory.sqlite")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + suffix)
        except OSError:
            pass
    ps = PersistentVectorStore(db_path=db_path)
    ps.add("c1", "苹果 手机 iPhone 价格 8999", meta={"source": "file", "filename": "a.txt", "entities": ["iPhone"]})
    ps.add("c2", "苹果 股票 AAPL 财报 2024 Q1", meta={"source": "file", "filename": "b.txt", "entities": ["AAPL"]})
    ps.add("c3", "香蕉 水果 维生素", meta={"source": "file", "filename": "c.txt"})
    hits = ps.search("苹果 财报", k=2, mmr_lambda=0.7, candidate_pool=6)
    assert hits and hits[0].id in {"c1", "c2"}
    cm2 = ContextManager(l1_max_turns=4, sink_turns=1, retrieval_k=2, store=ps, mmr_lambda=0.7, mmr_pool_mult=3)
    rr = cm2.retrieve("AAPL 财报", k=2)
    assert rr and any("AAPL" in (h.text or "") for h in rr)

    print("algo_smoke: ok")


if __name__ == "__main__":
    main()
