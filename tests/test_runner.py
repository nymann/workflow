from __future__ import annotations

from pathlib import Path

import pytest

from workflow import FunctionStep, StepResult, Workflow, python_step
from workflow.domain import CommandSpec, Context
from workflow.ports.out.command import CommandResult
from workflow.runner import Ports, Runner
from workflow.steps import command_step


class FakeClock:
    def __init__(self) -> None:
        self.value = 10.0

    def now_unix(self) -> float:
        return self.value

    def monotonic(self) -> float:
        self.value += 0.1
        return self.value


class FakeCommands:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.seen: list[CommandSpec] = []

    def run(self, spec: CommandSpec, *, workdir: Path) -> CommandResult:
        _ = workdir
        self.seen.append(spec)
        return self.result


class FakeMetrics:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def workflow_started(self, workflow: str, started_unix: float) -> None:
        self.events.append(("workflow-started", (workflow, started_unix)))

    def step_started(self, workflow: str, step_id: str) -> None:
        self.events.append(("step-started", (workflow, step_id)))

    def step_finished(self, workflow: str, step_report: object) -> None:
        self.events.append(("step-finished", (workflow, step_report)))

    def workflow_finished(self, report: object) -> None:
        self.events.append(("workflow-finished", report))


def test_runner_shares_context_between_steps(tmp_path: Path) -> None:
    def produce(ctx: Context, ports: Ports) -> StepResult:
        _ = ports
        ctx.state["value"] = 42
        return StepResult(output=42)

    def consume(ctx: Context, ports: Ports) -> StepResult:
        _ = ports
        return StepResult(status=str(ctx.state["value"]))

    metrics = FakeMetrics()
    workflow = Workflow(
        name="shared",
        steps=(
            python_step("produce", produce),
            python_step("consume", consume, depends_on=("produce",)),
        ),
    )

    report = Runner(Ports(metrics=metrics, clock=FakeClock())).run(
        workflow, workdir=tmp_path
    )

    assert report.ok
    assert [step.id for step in report.steps] == ["produce", "consume"]
    assert report.steps[1].status == "42"
    assert [event[0] for event in metrics.events] == [
        "workflow-started",
        "step-started",
        "step-finished",
        "step-started",
        "step-finished",
        "workflow-finished",
    ]


def test_runner_stops_on_failure(tmp_path: Path) -> None:
    def fail(ctx: Context, ports: Ports) -> StepResult:
        _ = ctx, ports
        return StepResult.fail("nope")

    def unreachable(ctx: Context, ports: Ports) -> StepResult:
        _ = ctx, ports
        raise AssertionError("must not run")

    workflow = Workflow(
        name="failure",
        steps=(
            python_step("fail", fail),
            python_step("unreachable", unreachable, depends_on=("fail",)),
        ),
    )

    report = Runner(Ports(clock=FakeClock())).run(workflow, workdir=tmp_path)

    assert not report.ok
    assert [step.id for step in report.steps] == ["fail"]
    assert report.steps[0].status == "nope"


def test_command_step_uses_command_port(tmp_path: Path) -> None:
    commands = FakeCommands(CommandResult(code=0, stdout="done\n", stderr=""))
    workflow = Workflow(
        name="commands",
        steps=(command_step("cmd", CommandSpec(("echo", "done"))),),
    )

    report = Runner(Ports(commands=commands, clock=FakeClock())).run(
        workflow, workdir=tmp_path
    )

    assert report.ok
    assert report.steps[0].status == "done"
    assert commands.seen[0].argv == ("echo", "done")


def test_runner_supports_typed_outputs_and_conditions(tmp_path: Path) -> None:
    def produce(ctx: Context, ports: Ports) -> StepResult[int]:
        _ = ctx, ports
        return StepResult(output=7)

    def selected(ctx: Context, ports: Ports) -> StepResult[str]:
        _ = ports
        value = ctx.output("produce", int)
        return StepResult(status=f"selected {value}", output="selected")

    def skipped(ctx: Context, ports: Ports) -> StepResult[str]:
        _ = ctx, ports
        raise AssertionError("condition should skip this step")

    workflow = Workflow(
        name="conditional",
        steps=(
            FunctionStep(
                id="produce",
                output_type=int,
                handler=produce,
            ),
            FunctionStep(
                id="selected",
                depends_on=("produce",),
                output_type=str,
                condition=lambda ctx: ctx.output("produce", int) == 7,
                handler=selected,
            ),
            FunctionStep(
                id="skipped",
                depends_on=("produce",),
                condition=lambda ctx: ctx.output("produce", int) != 7,
                handler=skipped,
            ),
        ),
    )

    report = Runner(Ports(clock=FakeClock())).run(workflow, workdir=tmp_path)

    assert report.ok
    assert report.steps[1].status == "selected 7"
    assert report.steps[2].skipped


def test_runner_rejects_wrong_output_type(tmp_path: Path) -> None:
    workflow = Workflow(
        name="bad-output",
        steps=(
            FunctionStep(
                id="produce",
                output_type=int,
                handler=lambda ctx, ports: StepResult(output="wrong"),
            ),
        ),
    )

    with pytest.raises(TypeError, match="expected int"):
        Runner(Ports(clock=FakeClock())).run(workflow, workdir=tmp_path)


def test_validation_rejects_unknown_dependency() -> None:
    workflow = Workflow(
        name="bad",
        steps=(python_step("x", lambda ctx, ports: None, depends_on=("missing",)),),
    )

    with pytest.raises(ValueError, match="unknown step"):
        workflow.validate()
