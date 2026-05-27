from __future__ import annotations


class OpenTelemetryMetricsRecorder:
    def __init__(self, meter_name: str = "workflow") -> None:
        try:
            from opentelemetry import metrics
        except ImportError as error:
            raise RuntimeError(
                "OpenTelemetryMetricsRecorder requires the opentelemetry-api package"
            ) from error
        self._meter = metrics.get_meter(meter_name)
        self._step_duration = self._meter.create_histogram(
            "workflow.step.duration_ms",
            unit="ms",
            description="Workflow step duration",
        )
        self._phase_duration = self._meter.create_histogram(
            "workflow.phase.duration_ms",
            unit="ms",
            description="Workflow phase duration",
        )

    def workflow_started(self, workflow: str, started_unix: float) -> None:
        _ = workflow, started_unix

    def step_started(self, workflow: str, step_id: str) -> None:
        _ = workflow, step_id

    def step_finished(self, workflow: str, step_report: object) -> None:
        self._step_duration.record(
            getattr(step_report, "duration_ms", 0),
            {
                "workflow": workflow,
                "step_id": getattr(step_report, "id", ""),
                "kind": getattr(step_report, "kind", ""),
                "ok": str(getattr(step_report, "ok", False)).lower(),
                "skipped": str(getattr(step_report, "skipped", False)).lower(),
            },
        )

    def phase_started(self, workflow: str, step_id: str, phase_id: str) -> None:
        _ = workflow, step_id, phase_id

    def phase_finished(
        self,
        workflow: str,
        step_id: str,
        phase_id: str,
        *,
        duration_ms: int,
        ok: bool = True,
    ) -> None:
        self._phase_duration.record(
            duration_ms,
            {
                "workflow": workflow,
                "step_id": step_id,
                "phase_id": phase_id,
                "ok": str(ok).lower(),
            },
        )

    def workflow_finished(self, report: object) -> None:
        _ = report
