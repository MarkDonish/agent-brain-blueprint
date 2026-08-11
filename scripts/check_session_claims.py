#!/usr/bin/env python3
"""Read-only validation of session claims in a Markdown vault."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.frontmatter import parse_frontmatter
from lib.schema import (
    ValidationIssue,
    frontmatter_errors_to_issues,
    issues_to_messages,
    load_enums,
    load_schema,
    parse_expires_at,
    validate_against_schema,
)


def safe_relative_path(root: Path, raw: str) -> str | None:
    if not raw or str(raw).startswith(("/", "~")) or "\\" in str(raw):
        return None
    parts = str(raw).split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    candidate = (root / raw).resolve(strict=False)
    try:
        return str(candidate.relative_to(root.resolve()))
    except ValueError:
        return None


def overlaps(left: str, right: str) -> bool:
    a, b = left.casefold().split("/"), right.casefold().split("/")
    return a == b or a[: len(b)] == b or b[: len(a)] == a


def normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def claim_result(
    root: Path,
    path: Path,
    *,
    now: datetime | None = None,
    fail_on_expired: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "errors": [],
        "warnings": [],
        "paths": [],
        "active": False,
        "expired": False,
    }
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve())
        text = resolved.read_text(encoding="utf-8")
    except (OSError, RuntimeError, ValueError, UnicodeError):
        result["errors"] = ["claim path is unreadable or outside the vault"]
        return result

    parsed = parse_frontmatter(text)
    issues = frontmatter_errors_to_issues(parsed.errors)
    issues.extend(validate_against_schema(parsed.data, load_schema("session_claim"), enums=load_enums()))
    data = parsed.data

    paths: list[str] = []
    planned = data.get("planned_paths")
    if isinstance(planned, list):
        for raw in planned:
            safe = safe_relative_path(root, str(raw))
            if safe is None:
                issues.append(ValidationIssue("planned_paths", f"unsafe planned path: {raw}"))
            else:
                paths.append(safe)

    if data.get("status") == "closed" and data.get("closeout_state") != "closed":
        issues.append(ValidationIssue("closeout_state", "closed status requires closed closeout_state"))

    expires_at = parse_expires_at(data.get("expires_at"))
    current = normalize_dt(now or datetime.now(timezone.utc))
    expired = bool(expires_at and normalize_dt(expires_at) <= current)
    status = str(data.get("status") or "")
    closeout = str(data.get("closeout_state") or "")
    active = status in {"active", "blocked"} and closeout != "closed" and not expired
    warnings: list[str] = []
    if expired and status in {"active", "blocked"} and closeout != "closed":
        warning = "claim expired; no longer treated as active"
        if fail_on_expired:
            issues.append(ValidationIssue("expires_at", warning))
        else:
            warnings.append(warning)

    result.update(
        {
            "errors": issues_to_messages(issues),
            "warnings": warnings,
            "paths": paths,
            "active": active,
            "expired": expired,
            "session_id": data.get("session_id"),
            "claimed_by": data.get("claimed_by"),
        }
    )
    return result


def collect_claim_paths(root: Path, claims_dir: Path) -> list[Path]:
    if not claims_dir.is_dir():
        return []
    paths: list[Path] = []
    for current, _, files in os.walk(claims_dir, followlinks=False):
        for name in files:
            if name.endswith(".md"):
                paths.append(Path(current) / name)
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--claims-dir", type=Path, default=Path("40_handoffs/session_claims"))
    parser.add_argument("--fail-on-expired", action="store_true")
    parser.add_argument("--now", default=None, help="ISO timestamp override for tests")
    args = parser.parse_args()
    root = args.root.resolve()
    claims_dir = args.claims_dir if args.claims_dir.is_absolute() else root / args.claims_dir
    try:
        claims_dir.resolve(strict=False).relative_to(root)
    except (OSError, RuntimeError, ValueError):
        print(
            json.dumps(
                {
                    "read_only": True,
                    "failure_count": 1,
                    "failures": [{"path": str(claims_dir), "errors": ["claims directory is outside the vault"]}],
                },
                indent=2,
            )
        )
        return 2

    now = parse_expires_at(args.now) if args.now else None
    results = [
        claim_result(root, path, now=now, fail_on_expired=args.fail_on_expired)
        for path in collect_claim_paths(root, claims_dir)
    ]
    active = [item for item in results if item["active"] and not item["errors"]]
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if any(overlaps(str(a), str(b)) for a in left["paths"] for b in right["paths"]):
                left["errors"].append(f"conflicts with {right['path']}")
                right["errors"].append(f"conflicts with {left['path']}")

    failures = [
        {"path": item["path"], "errors": item["errors"], "warnings": item["warnings"]}
        for item in results
        if item["errors"]
    ]
    warnings = [
        {"path": item["path"], "warnings": item["warnings"]}
        for item in results
        if item["warnings"] and not item["errors"]
    ]
    print(
        json.dumps(
            {
                "read_only": True,
                "checked_file_count": len(results),
                "active_claim_count": len([item for item in results if item["active"] and not item["errors"]]),
                "failure_count": len(failures),
                "warning_count": len(warnings),
                "failures": failures,
                "warnings": warnings,
            },
            indent=2,
        )
    )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
