from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    def now_unix(self) -> float: ...

    def monotonic(self) -> float: ...
