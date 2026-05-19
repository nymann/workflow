from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AgentHandoff:
    workflow: str
    step_id: str
    prompt: str
    artifacts: tuple[Path, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentHandoffResult:
    accepted: bool = False
    status: str = "no agent handoff adapter configured"


class AgentHandoffPort(Protocol):
    def request(self, handoff: AgentHandoff, *, workdir: Path) -> AgentHandoffResult: ...
