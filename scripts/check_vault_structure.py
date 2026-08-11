#!/usr/bin/env python3
"""Read-only check that a vault has the expected top-level skeleton."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.vault_layout import required_entries


def _check_entry(root: Path, rel: str, kind: str) -> list[str]:
    path = root / rel
    if not path.exists():
        return [f"missing required {kind}: {rel}"]
    if kind == "file":
        if path.is_dir():
            return [f"required file is a directory: {rel}"]
        if not path.is_file():
            return [f"required file is not a regular file: {rel}"]
    elif kind == "directory":
        if path.is_file():
            return [f"required directory is a file: {rel}"]
        if not path.is_dir():
            return [f"required directory is not a directory: {rel}"]
    else:
        return [f"unknown kind {kind!r} for {rel}"]
    return []


def check_structure(root: Path) -> dict[str, object]:
    root = root.resolve()
    failures: list[dict[str, object]] = []
    checked = 0

    for entry in required_entries(project=False):
        rel = str(entry["path"])
        kind = str(entry["kind"])
        checked += 1
        errors = _check_entry(root, rel, kind)
        if errors:
            failures.append({"path": rel, "errors": errors})

    projects = []
    projects_root = root / "10_projects"
    if projects_root.is_dir():
        for project in sorted(path for path in projects_root.iterdir() if path.is_dir()):
            project_missing: list[str] = []
            for entry in required_entries(project=True):
                rel = str(entry["path"])
                kind = str(entry["kind"])
                checked += 1
                errors = _check_entry(project, rel, kind)
                if errors:
                    project_missing.extend(errors)
            projects.append({"name": project.name, "missing": project_missing})
            if project_missing:
                failures.append(
                    {
                        "path": f"10_projects/{project.name}",
                        "errors": project_missing,
                    }
                )

    return {
        "read_only": True,
        "checked_path_count": checked,
        "project_count": len(projects),
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    report = check_structure(root)
    print(json.dumps(report, indent=2))
    return 0 if report["failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
