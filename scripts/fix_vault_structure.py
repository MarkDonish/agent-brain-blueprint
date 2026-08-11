#!/usr/bin/env python3
"""Create missing vault skeleton paths. Default is dry-run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.path_safety import PathSafetyError, project_dir, validate_project_slug
from lib.vault_format import default_manifest
from lib.vault_layout import required_entries
import json


def missing_entries(root: Path, project: str | None = None) -> list[tuple[Path, str]]:
    """Return list of (absolute path, kind) that are missing or wrong type."""
    missing: list[tuple[Path, str]] = []
    for entry in required_entries(project=False):
        rel = str(entry["path"])
        kind = str(entry["kind"])
        path = root / rel
        if not path.exists():
            missing.append((path, kind))
        elif kind == "file" and not path.is_file():
            missing.append((path, kind))
        elif kind == "directory" and not path.is_dir():
            missing.append((path, kind))
    if project:
        slug = validate_project_slug(project)
        base = project_dir(root, slug)
        for entry in required_entries(project=True):
            rel = str(entry["path"])
            kind = str(entry["kind"])
            path = base / rel
            if not path.exists():
                missing.append((path, kind))
            elif kind == "file" and not path.is_file():
                missing.append((path, kind))
            elif kind == "directory" and not path.is_dir():
                missing.append((path, kind))
    return missing


def apply(entries: list[tuple[Path, str]]) -> None:
    for path, kind in entries:
        if kind == "directory":
            if path.exists() and path.is_file():
                raise PathSafetyError(f"cannot create directory; file exists: {path}")
            path.mkdir(parents=True, exist_ok=True)
            continue
        # file
        if path.exists() and path.is_dir():
            raise PathSafetyError(f"cannot create file; directory exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue
        if path.name == ".gitkeep":
            path.write_text("", encoding="utf-8")
        elif path.name == "manifest.json" and path.parent.name == ".agent-brain":
            path.write_text(json.dumps(default_manifest(), indent=2) + "\n", encoding="utf-8")
        elif path.suffix == ".md":
            title = path.stem.replace("_", " ")
            path.write_text(
                f"# {title}\n\nPlaceholder created by fix_vault_structure.py.\n",
                encoding="utf-8",
            )
        else:
            path.write_text("", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--project", default=None)
    parser.add_argument("--apply", action="store_true", help="create missing paths (otherwise dry-run)")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    try:
        missing = missing_entries(root, args.project)
    except PathSafetyError as exc:
        parser.error(str(exc))
    print(f"vault: {root}")
    print(f"missing: {len(missing)}")
    for path, kind in missing:
        print(f"  - [{kind}] {path.relative_to(root)}")
    if args.apply:
        try:
            apply(missing)
        except PathSafetyError as exc:
            parser.error(str(exc))
        print("applied")
    else:
        print("dry-run only; re-run with --apply to create placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
