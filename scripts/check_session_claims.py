#!/usr/bin/env python3
"""Read-only, trusted-local validation of session claims in a Markdown vault."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


REQUIRED = ("session_id", "task", "claimed_at", "status", "planned_paths", "dry_run_status", "dry_run_command", "dry_run_evidence", "closeout_state", "closeout_summary", "next_action")
VALID_STATUS = {"active", "blocked", "closed"}
VALID_CLOSEOUT = {"open", "blocked", "closed"}


def parse_frontmatter(text: str) -> tuple[dict[str, object], list[str]]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}, ["missing frontmatter"]
    data: dict[str, object] = {}
    errors: list[str] = []
    current_list: str | None = None
    for raw in match.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s*(.+)$", raw)
        if item and current_list:
            data.setdefault(current_list, []).append(item.group(1).strip())
            continue
        field = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not field:
            errors.append(f"malformed frontmatter line: {raw}")
            continue
        key, value = field.groups()
        if key in data:
            errors.append(f"duplicate field: {key}")
            continue
        current_list = key if not value.strip() else None
        data[key] = [] if current_list else value.strip()
    return data, errors


def safe_relative_path(root: Path, raw: str) -> str | None:
    if not raw or raw.startswith(("/", "~")) or "\\" in raw or any(part in {"", ".", ".."} for part in raw.split("/")):
        return None
    candidate = (root / raw).resolve(strict=False)
    try:
        return str(candidate.relative_to(root.resolve()))
    except ValueError:
        return None


def claim_result(root: Path, path: Path) -> dict[str, object]:
    result: dict[str, object] = {"path": str(path), "errors": [], "paths": [], "active": False}
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve())
        text = resolved.read_text(encoding="utf-8")
    except (OSError, RuntimeError, ValueError, UnicodeError):
        result["errors"] = ["claim path is unreadable or outside the vault"]
        return result
    data, errors = parse_frontmatter(text)
    for field in REQUIRED:
        if not data.get(field):
            errors.append(f"missing field: {field}")
    if data.get("status") not in VALID_STATUS:
        errors.append("invalid status")
    if data.get("closeout_state") not in VALID_CLOSEOUT:
        errors.append("invalid closeout_state")
    paths = []
    for raw in data.get("planned_paths", []):
        safe = safe_relative_path(root, str(raw))
        if safe is None:
            errors.append(f"unsafe planned path: {raw}")
        else:
            paths.append(safe)
    if data.get("status") == "closed" and data.get("closeout_state") != "closed":
        errors.append("closed status requires closed closeout_state")
    result.update({"errors": errors, "paths": paths, "active": data.get("status") in {"active", "blocked"} and data.get("closeout_state") != "closed"})
    return result


def overlaps(left: str, right: str) -> bool:
    a, b = left.casefold().split("/"), right.casefold().split("/")
    return a == b or a[: len(b)] == b or b[: len(a)] == a


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--claims-dir", type=Path, default=Path("40_handoffs/session_claims"))
    args = parser.parse_args()
    root = args.root.resolve()
    claims_dir = args.claims_dir if args.claims_dir.is_absolute() else root / args.claims_dir
    try:
        claims_dir.resolve(strict=False).relative_to(root)
    except (OSError, RuntimeError, ValueError):
        print(json.dumps({"read_only": True, "failure_count": 1, "failures": [{"path": str(claims_dir), "errors": ["claims directory is outside the vault"]}]}, indent=2))
        return 2
    paths = [] if not claims_dir.is_dir() else [Path(current) / name for current, _, files in os.walk(claims_dir, followlinks=False) for name in files if name.endswith(".md")]
    results = [claim_result(root, path) for path in sorted(paths)]
    active = [item for item in results if item["active"] and not item["errors"]]
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if any(overlaps(a, b) for a in left["paths"] for b in right["paths"]):
                left["errors"].append(f"conflicts with {right['path']}")
                right["errors"].append(f"conflicts with {left['path']}")
    failures = [{"path": item["path"], "errors": item["errors"]} for item in results if item["errors"]]
    print(json.dumps({"read_only": True, "checked_file_count": len(results), "active_claim_count": len(active), "failure_count": len(failures), "failures": failures}, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
