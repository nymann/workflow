from __future__ import annotations

from typing import Protocol


class MetricsSink(Protocol):
    def write(self, report: object) -> None: ...
