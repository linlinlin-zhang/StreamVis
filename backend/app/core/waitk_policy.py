from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WaitKPolicy:
    step_chars: int = 120
    min_interval_ms: int = 700
    max_updates: int = 4

    _acc_chars: int = 0
    _last_emit_ms: int = -1
    _updates: int = 0

    def observe(self, *, delta: str, now_ms: int) -> bool:
        if self._updates >= max(0, int(self.max_updates)):
            return False
        if not delta:
            return False

        self._acc_chars += len(delta)
        boundary_hit = any(p in delta for p in ("。", "！", "？", ".", "!", "?", "\n"))

        step = max(1, int(self.step_chars))
        due_by_chars = self._acc_chars >= step
        due_by_boundary = boundary_hit and self._acc_chars >= max(12, step // 3)

        if not (due_by_chars or due_by_boundary):
            return False

        min_dt = max(0, int(self.min_interval_ms))
        if self._last_emit_ms >= 0 and now_ms - self._last_emit_ms < min_dt:
            return False

        self._updates += 1
        self._last_emit_ms = int(now_ms)
        self._acc_chars = 0
        return True

