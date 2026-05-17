from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from workflow.domain import CommandSpec


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0


class Clock(Protocol):
    def now_unix(self) -> float: ...

    def monotonic(self) -> float: ...


class CommandRunner(Protocol):
    def run(self, spec: CommandSpec, *, workdir: Path) -> CommandResult: ...


class MetricsSink(Protocol):
    def write(self, report: object) -> None: ...


class Notifier(Protocol):
    def notify(self, message: str) -> None: ...
