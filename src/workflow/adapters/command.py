from __future__ import annotations

import subprocess
import os
from pathlib import Path

from workflow.domain import CommandSpec
from workflow.ports import CommandResult


class SubprocessCommandRunner:
    def run(self, spec: CommandSpec, *, workdir: Path) -> CommandResult:
        cwd = spec.cwd or workdir
        completed = subprocess.run(
            spec.argv,
            cwd=cwd,
            env={**os.environ, **spec.env} if spec.env else None,
            shell=spec.shell,
            check=False,
            text=True,
            capture_output=True,
        )
        return CommandResult(
            code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
