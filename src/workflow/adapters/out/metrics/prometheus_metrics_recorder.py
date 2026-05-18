from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-Unix fallback
    fcntl = None  # type: ignore[assignment]


DEFAULT_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)


class PrometheusMetricsRecorder:
    def __init__(
        self,
        *,
        state_path: Path,
        addr: str | None = None,
        serve: bool = False,
    ) -> None:
        self._state_path = state_path
        self._addr = addr
        self._server: ThreadingHTTPServer | None = None
        if serve and addr:
            self._start_server(addr)

    def workflow_started(self, workflow: str, started_unix: float) -> None:
        def update(state: dict[str, Any]) -> None:
            item = _workflow_state(state, workflow)
            item["active"] = 1
            item["last_started_unix"] = started_unix
            item["last_observed_unix"] = time()

        self._update_state(update)

    def step_started(self, workflow: str, step_id: str) -> None:
        def update(state: dict[str, Any]) -> None:
            item = _step_state(state, workflow, step_id)
            item["active"] = 1
            item["last_started_unix"] = time()

        self._update_state(update)

    def step_finished(self, workflow: str, step_report: object) -> None:
        step = _to_mapping(step_report)
        step_id = str(step.get("id", ""))
        duration_seconds = _int(step.get("duration_ms")) / 1000
        ok = bool(step.get("ok"))
        skipped = bool(step.get("skipped"))

        def update(state: dict[str, Any]) -> None:
            item = _step_state(state, workflow, step_id)
            item["kind"] = str(step.get("kind", ""))
            item["ok"] = ok
            item["skipped"] = skipped
            item["active"] = 0
            item["runs_total"] = _int(item.get("runs_total")) + 1
            result_key = f"{str(ok).lower()}:{str(skipped).lower()}"
            runs_by_result = item.setdefault("runs_by_result", {})
            runs_by_result[result_key] = _int(runs_by_result.get(result_key)) + 1
            item["last_duration_seconds"] = duration_seconds
            item["duration_seconds_sum"] = (
                float(item.get("duration_seconds_sum", 0.0)) + duration_seconds
            )
            item["duration_seconds_count"] = (
                _int(item.get("duration_seconds_count")) + 1
            )
            buckets = item.setdefault("duration_seconds_buckets", {})
            for bucket in DEFAULT_BUCKETS:
                if duration_seconds <= bucket:
                    key = _bucket_key(bucket)
                    buckets[key] = _int(buckets.get(key)) + 1
            buckets["+Inf"] = _int(buckets.get("+Inf")) + 1

        self._update_state(update)

    def workflow_finished(self, report: object) -> None:
        run = _to_mapping(report)
        workflow = str(run.get("workflow", ""))
        ok = bool(run.get("ok"))
        duration_seconds = sum(
            _int(step.get("duration_ms")) / 1000
            for step in run.get("steps", [])
            if isinstance(step, dict)
        )

        def update(state: dict[str, Any]) -> None:
            item = _workflow_state(state, workflow)
            item["active"] = 0
            item["ok"] = ok
            item["runs_total"] = _int(item.get("runs_total")) + 1
            runs_by_ok = item.setdefault("runs_by_ok", {})
            ok_key = str(ok).lower()
            runs_by_ok[ok_key] = _int(runs_by_ok.get(ok_key)) + 1
            item["last_duration_seconds"] = duration_seconds
            item["duration_seconds_sum"] = (
                float(item.get("duration_seconds_sum", 0.0)) + duration_seconds
            )
            item["duration_seconds_count"] = (
                _int(item.get("duration_seconds_count")) + 1
            )
            item["last_observed_unix"] = time()

        self._update_state(update)

    def _start_server(self, addr: str) -> None:
        host, port = _parse_addr(addr)
        try:
            server = ThreadingHTTPServer(
                (host, port),
                _handler(self._state_path),
            )
        except OSError:
            return
        thread = threading.Thread(
            target=server.serve_forever,
            name="workflow-prometheus",
            daemon=True,
        )
        thread.start()
        self._server = server

    def _update_state(self, callback: Any) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self._state_path.with_suffix(self._state_path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lock:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = _read_state(self._state_path)
            callback(state)
            _write_state(self._state_path, state)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _handler(state_path: Path) -> type[BaseHTTPRequestHandler]:
    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/metrics":
                self.send_response(404)
                self.end_headers()
                return
            body = render_prometheus(_read_state(state_path)).encode("utf-8")
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            _ = format, args

    return MetricsHandler


def render_prometheus(state: dict[str, Any]) -> str:
    lines = [
        "# HELP workflow_runs_total Workflow runs by workflow and result.",
        "# TYPE workflow_runs_total counter",
    ]
    workflows = state.get("workflows", {})
    for workflow, item in sorted(workflows.items()):
        runs_by_ok = item.get("runs_by_ok", {})
        if not runs_by_ok:
            runs_by_ok = {str(bool(item.get("ok"))).lower(): item.get("runs_total", 0)}
        for ok, total in sorted(runs_by_ok.items()):
            labels = {"workflow": workflow, "ok": str(ok)}
            lines.append(_sample("workflow_runs_total", labels, _int(total)))
    lines.extend(
        [
            "# HELP workflow_active Active workflow runs.",
            "# TYPE workflow_active gauge",
        ]
    )
    for workflow, item in sorted(workflows.items()):
        lines.append(
            _sample("workflow_active", {"workflow": workflow}, _int(item.get("active")))
        )
        lines.append(
            _sample(
                "workflow_last_run_duration_seconds",
                {"workflow": workflow},
                float(item.get("last_duration_seconds", 0.0)),
            )
        )
        lines.append(
            _sample(
                "workflow_last_run_ok",
                {"workflow": workflow},
                1 if item.get("ok") else 0,
            )
        )
    lines.extend(
        [
            "# HELP workflow_run_duration_seconds Workflow run duration summary.",
            "# TYPE workflow_run_duration_seconds summary",
        ]
    )
    for workflow, item in sorted(workflows.items()):
        labels = {"workflow": workflow}
        lines.append(
            _sample(
                "workflow_run_duration_seconds_sum",
                labels,
                float(item.get("duration_seconds_sum", 0.0)),
            )
        )
        lines.append(
            _sample(
                "workflow_run_duration_seconds_count",
                labels,
                _int(item.get("duration_seconds_count")),
            )
        )

    steps = state.get("steps", {})
    lines.extend(
        [
            "# HELP workflow_step_runs_total Workflow step runs by result.",
            "# TYPE workflow_step_runs_total counter",
        ]
    )
    for key, item in sorted(steps.items()):
        workflow, step_id = key.split("\0", 1)
        runs_by_result = item.get("runs_by_result", {})
        if not runs_by_result:
            ok = str(bool(item.get("ok"))).lower()
            skipped = str(bool(item.get("skipped"))).lower()
            runs_by_result = {
                f"{ok}:{skipped}": item.get("runs_total", 0),
            }
        for result, total in sorted(runs_by_result.items()):
            ok, skipped = result.split(":", 1)
            labels = _step_labels(workflow, step_id, item, ok=ok, skipped=skipped)
            lines.append(
                _sample("workflow_step_runs_total", labels, _int(total))
            )
    lines.extend(
        [
            "# HELP workflow_step_active Active workflow steps.",
            "# TYPE workflow_step_active gauge",
        ]
    )
    for key, item in sorted(steps.items()):
        workflow, step_id = key.split("\0", 1)
        labels = {"workflow": workflow, "step_id": step_id, "kind": str(item.get("kind", ""))}
        lines.append(_sample("workflow_step_active", labels, _int(item.get("active"))))
        lines.append(
            _sample(
                "workflow_step_last_duration_seconds",
                labels,
                float(item.get("last_duration_seconds", 0.0)),
            )
        )
    lines.extend(
        [
            "# HELP workflow_step_duration_seconds Workflow step duration histogram.",
            "# TYPE workflow_step_duration_seconds histogram",
        ]
    )
    for key, item in sorted(steps.items()):
        workflow, step_id = key.split("\0", 1)
        labels = {"workflow": workflow, "step_id": step_id, "kind": str(item.get("kind", ""))}
        buckets = item.get("duration_seconds_buckets", {})
        cumulative = 0
        for bucket in DEFAULT_BUCKETS:
            key_name = _bucket_key(bucket)
            cumulative = _int(buckets.get(key_name))
            lines.append(
                _sample(
                    "workflow_step_duration_seconds_bucket",
                    {**labels, "le": key_name},
                    cumulative,
                )
            )
        lines.append(
            _sample(
                "workflow_step_duration_seconds_bucket",
                {**labels, "le": "+Inf"},
                _int(buckets.get("+Inf")),
            )
        )
        lines.append(
            _sample(
                "workflow_step_duration_seconds_sum",
                labels,
                float(item.get("duration_seconds_sum", 0.0)),
            )
        )
        lines.append(
            _sample(
                "workflow_step_duration_seconds_count",
                labels,
                _int(item.get("duration_seconds_count")),
            )
        )
    return "\n".join(lines) + "\n"


def _workflow_state(state: dict[str, Any], workflow: str) -> dict[str, Any]:
    return state.setdefault("workflows", {}).setdefault(workflow, {})


def _step_state(state: dict[str, Any], workflow: str, step_id: str) -> dict[str, Any]:
    return state.setdefault("steps", {}).setdefault(f"{workflow}\0{step_id}", {})


def _step_labels(
    workflow: str,
    step_id: str,
    item: dict[str, Any],
    *,
    ok: str,
    skipped: str,
) -> dict[str, str]:
    return {
        "workflow": workflow,
        "step_id": step_id,
        "kind": str(item.get("kind", "")),
        "ok": ok,
        "skipped": skipped,
    }


def _sample(name: str, labels: dict[str, str], value: int | float) -> str:
    label_text = ",".join(f'{key}="{_escape(value)}"' for key, value in labels.items())
    if isinstance(value, float) and not math.isfinite(value):
        value = 0
    return f"{name}{{{label_text}}} {value}"


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _bucket_key(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def _to_mapping(value: object) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.write("\n")
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _parse_addr(addr: str) -> tuple[str, int]:
    if ":" not in addr:
        return addr, 9102
    host, port = addr.rsplit(":", 1)
    return host, int(port)
