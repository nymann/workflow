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


class CommandRunner(Protocol):
    def run(self, spec: CommandSpec, *, workdir: Path) -> CommandResult: ...
