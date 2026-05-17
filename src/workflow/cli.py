from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow.adapters.out.metrics.json_metrics_recorder import JsonMetricsRecorder
from workflow.loader import load_workflow
from workflow.runner import Ports, Runner, report_to_dict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workflow")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("target", help="Python workflow target, e.g. package.mod:build")
    run_parser.add_argument("--workdir", default=".")
    run_parser.add_argument("--metrics")
    run_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "run":
        workdir = Path(args.workdir).resolve()
        sys.path.insert(0, str(workdir))
        workflow = load_workflow(args.target)
        metrics = JsonMetricsRecorder(Path(args.metrics)) if args.metrics else None
        ports = Ports(metrics=metrics) if metrics else Ports()
        report = Runner(ports).run(workflow, workdir=workdir)
        if args.json:
            print(json.dumps(report_to_dict(report), indent=2))
        else:
            print(f"{report.workflow}: {len(report.steps)} step(s), ok={report.ok}")
            for step in report.steps:
                print(f"- {step.id} [{step.kind}] {step.duration_ms}ms {step.status}")
        return 0 if report.ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
