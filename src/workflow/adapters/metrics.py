from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path


class NullMetricsSink:
    def write(self, report: object) -> None:
        _ = report


class JsonMetricsSink:
    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, report: object) -> None:
        if not is_dataclass(report):
            raise TypeError(f"expected dataclass report, got {type(report).__name__}")
        if self._path.parent:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(report), indent=2) + "\n")
