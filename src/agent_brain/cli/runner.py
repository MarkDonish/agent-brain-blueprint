"""Helpers to invoke legacy script entrypoints with controlled argv."""

from __future__ import annotations

import importlib
import sys
import io
from collections.abc import Sequence
from contextlib import contextmanager, redirect_stderr, redirect_stdout
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


def run_script_capture(module_name: str, argv: Sequence[str]) -> tuple[int, str, str]:
    """Import scripts/<module_name>.py and call main(), capturing stdout/stderr."""
    ensure_scripts_on_path()
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if main is None:
        raise RuntimeError(f"module {module_name} has no main()")
    out = io.StringIO()
    err = io.StringIO()
    with _argv([module_name, *argv]), redirect_stdout(out), redirect_stderr(err):
        try:
            code = main()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
    return int(code if code is not None else 0), out.getvalue(), err.getvalue()
