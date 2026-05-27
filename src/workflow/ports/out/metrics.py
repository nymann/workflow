from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class MetricsRecorder(Protocol):
    def workflow_started(self, workflow: str, started_unix: float) -> None: ...

    def step_started(self, workflow: str, step_id: str) -> None: ...

    def step_finished(self, workflow: str, step_report: object) -> None: ...

    def phase_started(self, workflow: str, step_id: str, phase_id: str) -> None: ...

    def phase_finished(
        self,
        workflow: str,
        step_id: str,
        phase_id: str,
        *,
        duration_ms: int,
        ok: bool = True,
    ) -> None: ...

    def workflow_finished(self, report: object) -> None: ...

    def gauge(
        self,
        name: str,
        value: int | float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None: ...

    def counter(
        self,
        name: str,
        value: int | float = 1,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None: ...
