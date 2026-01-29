from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.context_manager import ContextManager
from app.core.renderer import IncrementalRenderer
from app.core.token_budget import budget_messages, estimate_tokens


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

    print("algo_smoke: ok")


if __name__ == "__main__":
    main()
