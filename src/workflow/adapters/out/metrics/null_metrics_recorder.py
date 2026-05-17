from __future__ import annotations


class NullMetricsRecorder:
    def workflow_started(self, workflow: str, started_unix: float) -> None:
        _ = workflow, started_unix

    def step_started(self, workflow: str, step_id: str) -> None:
        _ = workflow, step_id

    def step_finished(self, workflow: str, step_report: object) -> None:
        _ = workflow, step_report

    def workflow_finished(self, report: object) -> None:
        _ = report
