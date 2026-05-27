from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping


class CompositeMetricsRecorder:
    def __init__(self, recorders: Iterable[object]) -> None:
        self._recorders = tuple(recorders)

    def workflow_started(self, workflow: str, started_unix: float) -> None:
        for recorder in self._recorders:
            recorder.workflow_started(workflow, started_unix)

    def step_started(self, workflow: str, step_id: str) -> None:
        for recorder in self._recorders:
            recorder.step_started(workflow, step_id)

    def step_finished(self, workflow: str, step_report: object) -> None:
        for recorder in self._recorders:
            recorder.step_finished(workflow, step_report)

    def phase_started(self, workflow: str, step_id: str, phase_id: str) -> None:
        for recorder in self._recorders:
            recorder.phase_started(workflow, step_id, phase_id)

    def phase_finished(
        self,
        workflow: str,
        step_id: str,
        phase_id: str,
        *,
        duration_ms: int,
        ok: bool = True,
    ) -> None:
        for recorder in self._recorders:
            recorder.phase_finished(
                workflow,
                step_id,
                phase_id,
                duration_ms=duration_ms,
                ok=ok,
            )

    def workflow_finished(self, report: object) -> None:
        for recorder in self._recorders:
            recorder.workflow_finished(report)

    def gauge(
        self,
        name: str,
        value: int | float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            recorder.gauge(name, value, labels=labels)

    def counter(
        self,
        name: str,
        value: int | float = 1,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        for recorder in self._recorders:
            recorder.counter(name, value, labels=labels)
