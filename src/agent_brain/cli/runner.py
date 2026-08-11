"""Helpers to invoke legacy script entrypoints with controlled argv."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Iterator

from agent_brain.paths import ensure_scripts_on_path


@contextmanager
def _argv(args: Sequence[str]) -> Iterator[None]:
    old = sys.argv
    sys.argv = list(args)
    try:
        yield
    finally:
        sys.argv = old


def run_script(module_name: str, argv: Sequence[str]) -> int:
    """Import scripts/<module_name>.py and call main() with argv[0]=module."""
    ensure_scripts_on_path()
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if main is None:
        raise RuntimeError(f"module {module_name} has no main()")
    with _argv([module_name, *argv]):
        code = main()
    return int(code if code is not None else 0)
