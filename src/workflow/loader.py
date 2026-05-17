from __future__ import annotations

import importlib
from collections.abc import Callable

from workflow.domain import Workflow


def load_workflow(target: str) -> Workflow:
    module_name, sep, attr_name = target.partition(":")
    if not sep or not module_name or not attr_name:
        raise ValueError("workflow target must look like 'module:attribute'")

    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    if isinstance(value, Workflow):
        return value
    if isinstance(value, Callable):
        workflow = value()
        if isinstance(workflow, Workflow):
            return workflow
    raise TypeError(f"{target!r} did not resolve to a Workflow")
