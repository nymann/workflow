from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast

if TYPE_CHECKING:
    from workflow.runner import Ports

StepKind = Literal["command", "deterministic", "gate", "llm", "notify"]
OutputT = TypeVar("OutputT")
Condition = Callable[["Context"], bool]


@dataclass(frozen=True)
class CommandSpec:
    argv: Sequence[str] | str
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    shell: bool = False


@dataclass
class Context:
    workdir: Path
    vars: dict[str, str] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)
    step_outputs: dict[str, Any] = field(default_factory=dict)

    def path(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.workdir / path

    def output(self, step_id: str, output_type: type[OutputT]) -> OutputT:
        if step_id not in self.step_outputs:
            raise KeyError(f"step {step_id!r} has no output")
        value = self.step_outputs[step_id]
        if not isinstance(value, output_type):
            raise TypeError(
                f"step {step_id!r} output is {type(value).__name__}, "
                f"expected {output_type.__name__}"
            )
        return cast(OutputT, value)


@dataclass
class StepResult(Generic[OutputT]):
    ok: bool = True
    status: str = "ok"
    output: OutputT | None = None

    @classmethod
    def fail(cls, status: str, output: Any = None) -> "StepResult[Any]":
        return cls(ok=False, status=status, output=output)


@dataclass(frozen=True)
class Step(ABC, Generic[OutputT]):
    id: str
    name: str | None = None
    kind: StepKind = "deterministic"
    depends_on: tuple[str, ...] = ()
    output_type: type[OutputT] | None = None
    condition: Condition | None = None

    def should_run(self, ctx: Context) -> bool:
        return self.condition(ctx) if self.condition else True

    @abstractmethod
    def run(self, ctx: Context, ports: "Ports") -> StepResult[OutputT] | None:
        raise NotImplementedError


@dataclass(frozen=True)
class Workflow:
    name: str
    steps: tuple[Step, ...]
    description: str | None = None
    vars: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("workflow name must not be empty")
        seen: set[str] = set()
        for step in self.steps:
            if not step.id.strip():
                raise ValueError("step id must not be empty")
            if step.id in seen:
                raise ValueError(f"duplicate step id {step.id!r}")
            seen.add(step.id)
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in seen:
                    raise ValueError(f"step {step.id!r} depends on unknown step {dep!r}")
