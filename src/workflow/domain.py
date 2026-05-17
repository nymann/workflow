from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from workflow.runner import Ports

StepKind = Literal["command", "deterministic", "gate", "llm", "notify"]
StepHandler = Callable[["Context", "Ports"], "StepResult | None"]


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


@dataclass(frozen=True)
class Step:
    id: str
    handler: StepHandler
    name: str | None = None
    kind: StepKind = "deterministic"
    depends_on: tuple[str, ...] = ()


@dataclass
class StepResult:
    ok: bool = True
    status: str = "ok"
    output: Any = None

    @classmethod
    def fail(cls, status: str, output: Any = None) -> "StepResult":
        return cls(ok=False, status=status, output=output)


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
