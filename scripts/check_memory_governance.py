#!/usr/bin/env python3
"""Read-only governance checks for durable and semi-durable vault records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.frontmatter import parse_frontmatter
from lib.schema import (
    frontmatter_errors_to_issues,
    issues_to_messages,
    load_enums,
    load_schema,
    validate_against_schema,
)

# directory relative glob, schema name, mode: strict|soft
TARGETS = (
    ("30_global_decisions/*.md", "memory_record", "strict"),
    ("10_projects/*/50_decisions/*.md", "memory_record", "strict"),
    ("10_projects/*/40_validation/*.md", "validation", "soft"),
    ("10_projects/*/20_handoffs/*.md", "handoff", "soft"),
    ("40_handoffs/session_claims/*.md", "session_claim", "soft"),
)

SKIP_NAMES = {"README.md", "INDEX.md", ".gitkeep"}


def iter_targets(root: Path, include_soft: bool = True):
    for pattern, schema_name, mode in TARGETS:
        if mode == "soft" and not include_soft:
            continue
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path.name in SKIP_NAMES:
                continue
            yield path, schema_name, mode


def check_file(root: Path, path: Path, schema_name: str, mode: str) -> dict[str, object]:
    relative = str(path.relative_to(root))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {"path": relative, "mode": mode, "errors": ["unreadable file"], "warnings": []}

    parsed = parse_frontmatter(text)
    # Soft directories may be plain index notes without frontmatter.
    if mode == "soft" and parsed.errors and not text.startswith("---"):
        return {
            "path": relative,
            "mode": mode,
            "errors": [],
            "warnings": ["missing frontmatter (soft target; ignored unless --strict-soft)"],
        }

    issues = frontmatter_errors_to_issues(parsed.errors)
    issues.extend(validate_against_schema(parsed.data, load_schema(schema_name), enums=load_enums()))
    errors = issues_to_messages(issues)
    warnings = [f"{item.field}: {item.message}" for item in issues if item.level == "warning"]
    return {"path": relative, "mode": mode, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--strict-soft", action="store_true", help="fail on soft-target warnings/errors")
    parser.add_argument("--no-soft", action="store_true", help="only check strict decision records")
    args = parser.parse_args()
    root = args.root.resolve()

    failures = []
    warnings = []
    checked = 0
    for path, schema_name, mode in iter_targets(root, include_soft=not args.no_soft):
        checked += 1
        result = check_file(root, path, schema_name, mode)
        if result["errors"]:
            if mode == "strict" or args.strict_soft:
                failures.append(result)
            else:
                warnings.append(result)
        elif result["warnings"]:
            warnings.append(result)

    print(
        json.dumps(
            {
                "read_only": True,
                "checked_file_count": checked,
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
