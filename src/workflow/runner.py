from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from workflow.adapters.inbound.clock.system_clock import SystemClock
from workflow.adapters.out.command.subprocess_command_runner import SubprocessCommandRunner
from workflow.adapters.out.metrics.null_metrics_recorder import NullMetricsRecorder
from workflow.adapters.out.notification.null_notifier import NullNotifier
from workflow.domain import Context, StepResult, Workflow
from workflow.ports.inbound.clock import Clock
from workflow.ports.out.command import CommandRunner
from workflow.ports.out.metrics import MetricsRecorder
from workflow.ports.out.notification import Notifier


@dataclass
class Ports:
    commands: CommandRunner = field(default_factory=SubprocessCommandRunner)
    metrics: MetricsRecorder = field(default_factory=NullMetricsRecorder)
    notifier: Notifier = field(default_factory=NullNotifier)
    clock: Clock = field(default_factory=SystemClock)


@dataclass(frozen=True)
class StepReport:
    id: str
    name: str
    kind: str
    ok: bool
    status: str
    duration_ms: int
    skipped: bool = False


@dataclass(frozen=True)
class RunReport:
    workflow: str
    ok: bool
    started_unix: float
    steps: tuple[StepReport, ...]


class Runner:
    def __init__(self, ports: Ports | None = None) -> None:
        self._ports = ports or Ports()

    def run(self, workflow: Workflow, *, workdir: Path) -> RunReport:
        workflow.validate()
        ctx = Context(workdir=workdir, vars=dict(workflow.vars))
        completed: dict[str, bool] = {}
        reports: list[StepReport] = []
        started = self._ports.clock.now_unix()
        self._ports.metrics.workflow_started(workflow.name, started)

        for step in workflow.steps:
            for dep in step.depends_on:
                if completed.get(dep) is not True:
                    raise RuntimeError(
                        f"step {step.id!r} dependency {dep!r} did not complete"
                    )

            if not step.should_run(ctx):
                completed[step.id] = True
                report = StepReport(
                    id=step.id,
                    name=step.name or step.id,
                    kind=step.kind,
                    ok=True,
                    status="skipped",
                    duration_ms=0,
                    skipped=True,
                )
                reports.append(report)
                self._ports.metrics.step_finished(workflow.name, report)
                continue

            self._ports.metrics.step_started(workflow.name, step.id)
            before = self._ports.clock.monotonic()
            raw_result = step.run(ctx, self._ports)
            result = raw_result or StepResult()
            duration_ms = int((self._ports.clock.monotonic() - before) * 1000)
            if result.ok and step.output_type and result.output is not None:
                if not isinstance(result.output, step.output_type):
                    raise TypeError(
                        f"step {step.id!r} returned {type(result.output).__name__}, "
                        f"expected {step.output_type.__name__}"
                    )
            ctx.step_outputs[step.id] = result.output
            completed[step.id] = result.ok
            step_report = StepReport(
                id=step.id,
                name=step.name or step.id,
                kind=step.kind,
                ok=result.ok,
                status=result.status,
                duration_ms=duration_ms,
            )
            reports.append(step_report)
            self._ports.metrics.step_finished(workflow.name, step_report)
            if not result.ok:
                report = self._report(workflow.name, False, started, reports)
                self._ports.metrics.workflow_finished(report)
                return report

        report = self._report(workflow.name, True, started, reports)
        self._ports.metrics.workflow_finished(report)
        return report

    @staticmethod
    def _report(
        workflow_name: str, ok: bool, started: float, steps: list[StepReport]
    ) -> RunReport:
        return RunReport(
            workflow=workflow_name,
            ok=ok,
            started_unix=started,
            steps=tuple(steps),
        )


def report_to_dict(report: RunReport) -> dict[str, Any]:
    return {
        "workflow": report.workflow,
        "ok": report.ok,
        "started_unix": report.started_unix,
        "steps": [
            {
                "id": step.id,
                "name": step.name,
                "kind": step.kind,
                "ok": step.ok,
                "status": step.status,
                "duration_ms": step.duration_ms,
                "skipped": step.skipped,
            }
            for step in report.steps
        ],
    }
