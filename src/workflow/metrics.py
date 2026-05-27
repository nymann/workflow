from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import monotonic


@contextmanager
def workflow_phase(
    metrics: object,
    workflow: str,
    step_id: str,
    phase_id: str,
) -> Iterator[None]:
    started = monotonic()
    ok = False
    phase_started = getattr(metrics, "phase_started", None)
    if phase_started:
        phase_started(workflow, step_id, phase_id)
    try:
        yield
        ok = True
    finally:
        phase_finished = getattr(metrics, "phase_finished", None)
        if phase_finished:
            phase_finished(
                workflow,
                step_id,
                phase_id,
                duration_ms=int((monotonic() - started) * 1000),
                ok=ok,
            )
