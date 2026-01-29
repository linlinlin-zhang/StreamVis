from __future__ import annotations

from typing import Any, Dict, List


class ContextManager:
    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def clear(self) -> None:
        self.history.clear()

    def add_user_input(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})

    def add_assistant_output(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})

    def get_recent_context(self, k: int = 6) -> List[Dict[str, Any]]:
        if k <= 0:
            return []
        return self.history[-k:]

    def get_context_vector(self) -> List[float]:
        return [0.1, 0.2, 0.3]
