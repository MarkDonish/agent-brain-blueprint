#!/usr/bin/env python3
"""Read-only governance checks for durable and semi-durable vault records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
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
    validate_against_schema,
)
from lib.vault_layout import VaultLayout, VaultLayoutError, detect_layout

SKIP_NAMES = {"README.md", "INDEX.md", ".gitkeep"}
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_YAML_BLOCK_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def _target_specs(layout: VaultLayout) -> tuple[tuple[str, str, str], ...]:
    """Build governance globs from the selected layout vocabulary."""

    projects = layout.projects_root_rel
    return (
        (f"{layout.relative_path('global_decisions')}/*.md", "memory_record", "strict"),
        (f"{projects}/*/{layout.relative_path('decisions')}/*.md", "memory_record", "strict"),
        (f"{projects}/*/{layout.relative_path('validation')}/*.md", "validation", "soft"),
        (f"{projects}/*/{layout.relative_path('handoffs')}/*.md", "handoff", "soft"),
        (f"{layout.claims_root_rel}/*.md", "session_claim", "soft"),
    )


def iter_targets(
    root: Path,
    include_soft: bool = True,
    *,
    layout: VaultLayout | None = None,
):
    selected = layout or detect_layout(root, strict=True)
    index_names = SKIP_NAMES | set(selected.index_files.values())
    for pattern, schema_name, mode in _target_specs(selected):
        if mode == "soft" and not include_soft:
            continue
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path.name in index_names:
                continue
            yield path, schema_name, mode


def _parse_date_like(value: object) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    match = _DATE_RE.match(text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def lifecycle_issues(data: dict, schema_name: str, *, today: date | None = None) -> list[ValidationIssue]:
    """Extra behavioral rules beyond field shapes."""
    issues: list[ValidationIssue] = []
    today = today or datetime.now(timezone.utc).date()

    risk = str(data.get("risk_boundary") or "")
    confidence = str(data.get("confidence") or "")
    if risk == "production" and confidence and confidence != "verified":
        issues.append(
            ValidationIssue(
                "confidence",
                "production risk_boundary requires confidence=verified",
            )
        )

    state = str(data.get("state") or "")
    freshness = str(data.get("freshness") or "")
    if state == "superseded":
        issues.append(
            ValidationIssue(
                "state",
                "superseded records should not be treated as active context",
                level="warning",
            )
        )
    if freshness == "expired":
        issues.append(
            ValidationIssue(
                "freshness",
                "expired freshness must not be used as current fact",
                level="warning",
            )
        )

    for field in ("review_after", "next_review"):
        review = _parse_date_like(data.get(field))
        if review is not None and review < today:
            issues.append(
                ValidationIssue(
                    field,
                    f"{field} is in the past; mark review-required or refresh the record",
                    level="warning",
                )
            )

    if schema_name == "validation" and str(data.get("status") or "") == "pass":
        has_commands = bool(str(data.get("commands") or "").strip())
        has_evidence = bool(
            str(data.get("evidence_ref") or data.get("evidence") or "").strip()
        )
        if not has_commands and not has_evidence:
            issues.append(
                ValidationIssue(
                    "status",
                    "status=pass requires commands or evidence_ref/evidence (self-attest alone is insufficient)",
                    level="warning",
                )
            )

    return issues


def check_file(
    root: Path,
    path: Path,
    schema_name: str,
    mode: str,
    *,
    layout: VaultLayout | None = None,
) -> dict[str, object]:
    relative = str(path.relative_to(root))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {"path": relative, "mode": mode, "errors": ["unreadable file"], "warnings": []}

    parsed = parse_frontmatter(text)
    if (
        layout is not None
        and layout.layout_id == "agent-brain-zh-v1"
        and not text.startswith("---")
    ):
        # The canonical Chinese governance template historically stores its
        # metadata in a fenced YAML block below the title. Treat that block as
        # the record header without weakening strict frontmatter elsewhere.
        match = _YAML_BLOCK_RE.search(text)
        if match:
            parsed = parse_frontmatter(f"---\n{match.group(1)}\n---\n")
    # Soft directories may be plain index notes without frontmatter.
    if mode == "soft" and parsed.errors and not text.startswith("---"):
        return {
            "path": relative,
            "mode": mode,
            "errors": [],
            "warnings": ["missing frontmatter (soft target; ignored unless --strict-soft)"],
        }

    issues = frontmatter_errors_to_issues(parsed.errors)
    issues.extend(
        validate_against_schema(
            parsed.data,
            load_schema(schema_name),
            enums=load_enums(),
            relaxed_enum_fields=(
                layout.relaxed_enum_fields(schema_name) if layout is not None else frozenset()
            ),
        )
    )
    issues.extend(lifecycle_issues(parsed.data, schema_name))
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

    try:
        layout = detect_layout(root, strict=True)
    except VaultLayoutError as exc:
        print(
            json.dumps(
                {
                    "read_only": True,
                    "layout_id": None,
                    "layout": None,
                    "checked_file_count": 0,
                    "failure_count": 1,
                    "warning_count": 0,
                    "failures": [],
                    "warnings": [],
                    "errors": [str(exc)],
                },
                indent=2,
            )
        )
        return 2

    failures = []
    warnings = []
    checked = 0
    for path, schema_name, mode in iter_targets(
        root,
        include_soft=not args.no_soft,
        layout=layout,
    ):
        checked += 1
        result = check_file(root, path, schema_name, mode, layout=layout)
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
                "layout_id": layout.layout_id,
                "layout": layout.layout_id,
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
