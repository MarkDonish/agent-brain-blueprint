"""Generation filesystem primitives shared by the retrieval index builder."""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterator


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def generation_id() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]


@contextlib.contextmanager
def build_lock(index_root: Path, *, timeout: float = 10.0, poll: float = 0.05) -> Iterator[None]:
    """Acquire a short-lived cross-process directory lock."""

    index_root.mkdir(parents=True, exist_ok=True)
    lock = index_root / ".build.lock"
    deadline = time.monotonic() + max(0.0, float(timeout))
    acquired = False
    while True:
        try:
            lock.mkdir()
            acquired = True
            try:
                (lock / "owner.json").write_text(
                    json.dumps({"pid": os.getpid(), "created_at": utc_now()}), encoding="utf-8"
                )
            except OSError:
                pass
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"retrieval build lock busy: {lock}")
            time.sleep(min(max(0.001, poll), max(0.001, deadline - time.monotonic())))
    try:
        yield
    finally:
        if acquired:
            shutil.rmtree(lock, ignore_errors=True)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def run_failure_hook(failure_inject: Callable[[str], Any] | None, stage: str) -> None:
    if failure_inject:
        try:
            failure_inject(stage)
        except TypeError:
            # A tiny no-argument hook is convenient in tests.
            failure_inject()  # type: ignore[call-arg]


__all__ = ["build_lock", "generation_id", "run_failure_hook", "utc_now", "write_json_atomic"]
