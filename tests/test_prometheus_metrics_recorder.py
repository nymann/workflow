from __future__ import annotations

from pathlib import Path

from workflow.adapters.out.metrics.prometheus_metrics_recorder import (
    PrometheusMetricsRecorder,
    render_prometheus,
)
from workflow.runner import RunReport, StepReport


def test_prometheus_recorder_renders_step_duration_metrics(tmp_path: Path) -> None:
    state = tmp_path / "prometheus-state.json"
    recorder = PrometheusMetricsRecorder(state_path=state)

    recorder.workflow_started("demo", 10.0)
    recorder.step_started("demo", "first")
    recorder.step_finished(
        "demo",
        StepReport(
            id="first",
            name="First",
            kind="deterministic",
            ok=True,
            status="ok",
            duration_ms=1500,
        ),
    )
    recorder.workflow_finished(
        RunReport(
            workflow="demo",
            ok=True,
            started_unix=10.0,
            steps=(
                StepReport(
                    id="first",
                    name="First",
                    kind="deterministic",
                    ok=True,
                    status="ok",
                    duration_ms=1500,
                ),
            ),
        )
    )

    text = render_prometheus(__import__("json").loads(state.read_text()))

    assert 'workflow_runs_total{workflow="demo",ok="true"} 1' in text
    assert (
        'workflow_step_runs_total{workflow="demo",step_id="first",'
        'kind="deterministic",ok="true",skipped="false"} 1'
    ) in text
    assert (
        'workflow_step_last_duration_seconds{workflow="demo",step_id="first",'
        'kind="deterministic"} 1.5'
    ) in text
    assert (
        'workflow_step_duration_seconds_bucket{workflow="demo",step_id="first",'
        'kind="deterministic",le="2.5"} 1'
    ) in text


def test_prometheus_recorder_accumulates_across_instances(tmp_path: Path) -> None:
    state = tmp_path / "prometheus-state.json"

    for _ in range(2):
        recorder = PrometheusMetricsRecorder(state_path=state)
        recorder.workflow_started("demo", 10.0)
        recorder.workflow_finished(
            RunReport(workflow="demo", ok=True, started_unix=10.0, steps=())
        )

    text = render_prometheus(__import__("json").loads(state.read_text()))

    assert 'workflow_runs_total{workflow="demo",ok="true"} 2' in text


def test_prometheus_recorder_renders_custom_metrics(tmp_path: Path) -> None:
    state = tmp_path / "prometheus-state.json"
    recorder = PrometheusMetricsRecorder(state_path=state)

    recorder.gauge(
        "mutation_coverage_ratio",
        0.75,
        labels={"target_class": "com.acme.LegacyThing"},
    )
    recorder.counter(
        "attempts",
        labels={"target_class": "com.acme.LegacyThing", "result": "kept"},
    )
    recorder.counter(
        "attempts",
        labels={"target_class": "com.acme.LegacyThing", "result": "kept"},
    )

    text = render_prometheus(__import__("json").loads(state.read_text()))

    assert 'mutation_coverage_ratio{target_class="com.acme.LegacyThing"} 0.75' in text
    assert (
        'attempts_total{result="kept",target_class="com.acme.LegacyThing"} 2.0'
    ) in text


def test_prometheus_recorder_renders_active_step_duration(tmp_path: Path) -> None:
    state = tmp_path / "prometheus-state.json"
    recorder = PrometheusMetricsRecorder(state_path=state)

    recorder.workflow_started("demo", 10.0)
    recorder.step_started("demo", "slow")

    text = render_prometheus(__import__("json").loads(state.read_text()))

    assert (
        'workflow_step_active_duration_seconds{workflow="demo",step_id="slow",'
        'kind=""}'
    ) in text


def test_prometheus_recorder_renders_phase_duration_metrics(tmp_path: Path) -> None:
    state = tmp_path / "prometheus-state.json"
    recorder = PrometheusMetricsRecorder(state_path=state)

    recorder.phase_started("demo", "loop", "agent")
    recorder.phase_finished(
        "demo",
        "loop",
        "agent",
        duration_ms=2500,
    )

    text = render_prometheus(__import__("json").loads(state.read_text()))

    assert (
        'workflow_phase_runs_total{workflow="demo",step_id="loop",'
        'phase_id="agent",ok="true"} 1'
    ) in text
    assert (
        'workflow_phase_last_duration_seconds{workflow="demo",step_id="loop",'
        'phase_id="agent"} 2.5'
    ) in text
    assert (
        'workflow_phase_duration_seconds_bucket{workflow="demo",step_id="loop",'
        'phase_id="agent",le="2.5"} 1'
    ) in text
