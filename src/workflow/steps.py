from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from workflow.domain import CommandSpec, Context, Step, StepResult
from workflow.runner import Ports


@dataclass(frozen=True)
class CommandStep(Step):
    command: CommandSpec = CommandSpec(())

    def run(self, ctx: Context, ports: Ports) -> StepResult:
        result = ports.commands.run(self.command, workdir=ctx.workdir)
        output = {
            "code": result.code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        if result.ok:
            status = "ok"
            if result.stdout.strip():
                status = result.stdout.strip().splitlines()[-1]
            return StepResult(ok=True, status=status, output=output)
        return StepResult.fail(
            f"exit {result.code}: {result.stderr or result.stdout}", output=output
        )


@dataclass(frozen=True)
class FunctionStep(Step):
    handler: Callable[[Context, Ports], StepResult | None] = lambda ctx, ports: None

    def run(self, ctx: Context, ports: Ports) -> StepResult | None:
        return self.handler(ctx, ports)


def command_step(
    step_id: str,
    command: CommandSpec,
    *,
    name: str | None = None,
    depends_on: tuple[str, ...] = (),
    kind: str = "command",
) -> Step:
    return CommandStep(
        id=step_id,
        name=name,
        kind=kind,  # type: ignore[arg-type]
        depends_on=depends_on,
        command=command,
    )


def python_step(
    step_id: str,
    handler: Callable[[Context, Ports], StepResult | None],
    *,
    name: str | None = None,
    depends_on: tuple[str, ...] = (),
    kind: str = "deterministic",
) -> Step:
    return FunctionStep(
        id=step_id,
        name=name,
        kind=kind,  # type: ignore[arg-type]
        depends_on=depends_on,
        handler=handler,
    )
