from __future__ import annotations

from pathlib import Path

from workflow.ports.out.agent import AgentHandoff, AgentHandoffResult


class NullAgentHandoffPort:
    def request(self, handoff: AgentHandoff, *, workdir: Path) -> AgentHandoffResult:
        _ = handoff, workdir
        return AgentHandoffResult()
