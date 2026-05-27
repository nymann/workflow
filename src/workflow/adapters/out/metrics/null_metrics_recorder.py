from __future__ import annotations

from collections.abc import Mapping


class NullMetricsRecorder:
    def workflow_started(self, workflow: str, started_unix: float) -> None:
        _ = workflow, started_unix

    def step_started(self, workflow: str, step_id: str) -> None:
        _ = workflow, step_id

    def step_finished(self, workflow: str, step_report: object) -> None:
        _ = workflow, step_report

    def workflow_finished(self, report: object) -> None:
        _ = report

    def gauge(
        self,
        name: str,
        value: int | float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        _ = name, value, labels

    def counter(
        self,
        name: str,
        value: int | float = 1,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        _ = name, value, labels
