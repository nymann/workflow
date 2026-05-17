from __future__ import annotations

from workflow import CommandSpec, StepResult, Workflow, command_step, python_step
from workflow.domain import Context
from workflow.runner import Ports


def remember(ctx: Context, ports: Ports) -> StepResult:
    _ = ports
    ctx.state["message"] = "hello from shared context"
    return StepResult(status="remembered", output={"message": ctx.state["message"]})


def observe(ctx: Context, ports: Ports) -> StepResult:
    _ = ports
    return StepResult(status=str(ctx.state["message"]), output=ctx.state["message"])


def build() -> Workflow:
    return Workflow(
        name="echo",
        description="Small workflow demonstrating Python steps and command steps.",
        steps=(
            python_step("remember", remember),
            python_step("observe", observe, depends_on=("remember",)),
            command_step(
                "echo",
                CommandSpec(("python", "-c", "print('command adapter ok')")),
                depends_on=("observe",),
            ),
        ),
    )
