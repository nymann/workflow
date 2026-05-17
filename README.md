# Workflow

Workflow is a Python experiment for reusable agent and grammar pipelines.

The core is intentionally small and ports-and-adapters shaped:

- `workflow.domain`: workflow, step, context, and command data structures.
- `workflow.runner`: dependency ordering, shared context, reports, and ports.
- `workflow.ports`: command, metrics, notification, and clock protocols.
- `workflow.adapters`: subprocess, JSON metrics, stdout/null notification, and clock adapters.

Workflow definitions are Python code. A repository can import this library,
register project-specific steps, and share state through `Context` without
encoding pipeline behavior in TOML strings.

## Setup

```sh
uv sync
```

This project targets Python 3.14.

## Run The Example

```sh
uv run workflow run examples.echo_workflow:build
uv run workflow run examples.echo_workflow:build --json --metrics .workflow/echo.json
```

The CLI adds `--workdir` to `sys.path` before loading the workflow target, so a
consumer repository can keep workflow definitions in its own tree.

## Define A Workflow

```python
from workflow import CommandSpec, Workflow, command_step


def build() -> Workflow:
    return Workflow(
        name="example",
        steps=(
            command_step(
                "hello",
                CommandSpec(("python", "-c", "print('hello')")),
            ),
        ),
    )
```

Run it with:

```sh
uv run workflow run my_workflows.example:build --workdir /path/to/repo
```

## Near-Term Direction

The next useful layer is not more CLI syntax. It is stronger library contracts:

- typed step outputs,
- resumable state,
- retry and repair policies,
- LLM and notification adapters,
- richer metrics sinks,
- parallel execution groups.
