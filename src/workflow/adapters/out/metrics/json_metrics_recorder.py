from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class MetricEvent:
    kind: Literal[
        "workflow-started",
        "step-started",
        "step-finished",
        "phase-started",
        "phase-finished",
        "workflow-finished",
        "gauge",
        "counter",
    ]
    workflow: str | None
    payload: object


class JsonMetricsRecorder:
    def __init__(self, path: Path) -> None:
        self._path = path

    def workflow_started(self, workflow: str, started_unix: float) -> None:
        self._append(
            MetricEvent(
                kind="workflow-started",
                workflow=workflow,
                payload={"started_unix": started_unix},
            )
        )

    def step_started(self, workflow: str, step_id: str) -> None:
        self._append(
            MetricEvent(
                kind="step-started",
                workflow=workflow,
                payload={"step_id": step_id},
            )
        )

    def step_finished(self, workflow: str, step_report: object) -> None:
        self._append(
            MetricEvent(kind="step-finished", workflow=workflow, payload=step_report)
        )

    def phase_started(self, workflow: str, step_id: str, phase_id: str) -> None:
        self._append(
            MetricEvent(
                kind="phase-started",
                workflow=workflow,
                payload={"step_id": step_id, "phase_id": phase_id},
            )
        )

    def phase_finished(
        self,
        workflow: str,
        step_id: str,
        phase_id: str,
        *,
        duration_ms: int,
        ok: bool = True,
    ) -> None:
        self._append(
            MetricEvent(
                kind="phase-finished",
                workflow=workflow,
                payload={
                    "step_id": step_id,
                    "phase_id": phase_id,
                    "duration_ms": duration_ms,
                    "ok": ok,
                },
            )
        )

    def workflow_finished(self, report: object) -> None:
        self._append(
            MetricEvent(
                kind="workflow-finished",
                workflow=getattr(report, "workflow", ""),
                payload=report,
            )
        )
        if self._path.suffix == ".json":
            self._write_json_report(report)

    def gauge(
        self,
        name: str,
        value: int | float,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        self._append(
            MetricEvent(
                kind="gauge",
                workflow=None,
                payload={
                    "name": name,
                    "value": value,
                    "labels": dict(labels or {}),
                },
            )
        )

    def counter(
        self,
        name: str,
        value: int | float = 1,
        *,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        self._append(
            MetricEvent(
                kind="counter",
                workflow=None,
                payload={
                    "name": name,
                    "value": value,
                    "labels": dict(labels or {}),
                },
            )
        )

    def _append(self, event: MetricEvent) -> None:
        if self._path.parent:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.suffix == ".jsonl":
            self._path.open("a").write(json.dumps(_to_jsonable(event)) + "\n")

    def _write_json_report(self, report: object) -> None:
        if not is_dataclass(report):
            raise TypeError(f"expected dataclass report, got {type(report).__name__}")
        if self._path.parent:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(report), indent=2) + "\n")


def _to_jsonable(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    return value
