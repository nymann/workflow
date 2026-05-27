from __future__ import annotations

import pytest

from workflow.metrics import workflow_phase


class FakeMetrics:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def phase_started(self, workflow: str, step_id: str, phase_id: str) -> None:
        self.events.append(("phase-started", (workflow, step_id, phase_id)))

    def phase_finished(
        self,
        workflow: str,
        step_id: str,
        phase_id: str,
        *,
        duration_ms: int,
        ok: bool = True,
    ) -> None:
        self.events.append(
            (
                "phase-finished",
                {
                    "workflow": workflow,
                    "step_id": step_id,
                    "phase_id": phase_id,
                    "duration_ms": duration_ms,
                    "ok": ok,
                },
            )
        )


def test_workflow_phase_records_success() -> None:
    metrics = FakeMetrics()

    with workflow_phase(metrics, "demo", "loop", "agent"):
        pass

    assert metrics.events[0] == ("phase-started", ("demo", "loop", "agent"))
    assert metrics.events[1][0] == "phase-finished"
    assert metrics.events[1][1]["ok"] is True


def test_workflow_phase_records_failure() -> None:
    metrics = FakeMetrics()

    with pytest.raises(RuntimeError):
        with workflow_phase(metrics, "demo", "loop", "agent"):
            raise RuntimeError("boom")

    assert metrics.events[1][1]["ok"] is False
