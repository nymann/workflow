from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from workflow.adapters.clock import SystemClock
from workflow.adapters.command import SubprocessCommandRunner
from workflow.adapters.metrics import NullMetricsSink
from workflow.adapters.notify import NullNotifier
from workflow.domain import Context, StepResult, Workflow
from workflow.ports import Clock, CommandRunner, MetricsSink, Notifier


@dataclass
class Ports:
    commands: CommandRunner = field(default_factory=SubprocessCommandRunner)
    metrics: MetricsSink = field(default_factory=NullMetricsSink)
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

        for step in workflow.steps:
            for dep in step.depends_on:
                if completed.get(dep) is not True:
                    raise RuntimeError(
                        f"step {step.id!r} dependency {dep!r} did not complete"
                    )

            before = self._ports.clock.monotonic()
            raw_result = step.handler(ctx, self._ports)
            result = raw_result or StepResult()
            duration_ms = int((self._ports.clock.monotonic() - before) * 1000)
            ctx.step_outputs[step.id] = result.output
            completed[step.id] = result.ok
            reports.append(
                StepReport(
                    id=step.id,
                    name=step.name or step.id,
                    kind=step.kind,
                    ok=result.ok,
                    status=result.status,
                    duration_ms=duration_ms,
                )
            )
            if not result.ok:
                report = self._report(workflow.name, False, started, reports)
                self._ports.metrics.write(report)
                return report

        report = self._report(workflow.name, True, started, reports)
        self._ports.metrics.write(report)
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
            }
            for step in report.steps
        ],
    }
