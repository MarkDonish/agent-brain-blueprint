#!/usr/bin/env python3
"""Schema loader/validator for Agent Brain Blueprint (JSON schemas, no third-party deps)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .frontmatter import FrontmatterError


SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    level: str = "error"  # error | warning


def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_enums() -> dict[str, list[str]]:
    data = load_json_file(SCHEMAS_DIR / "enums.json")
    return {key: [str(item) for item in value] for key, value in data.items() if isinstance(value, list)}


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMAS_DIR / f"{name}.json"
    if not path.exists():
        # backward-compatible: allow .yaml name mapping if only json exists
        raise FileNotFoundError(path)
    return load_json_file(path)


def _is_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        return False


def _is_safe_rel_path(value: str) -> bool:
    if not value or value.startswith(("/", "~")) or "\\" in value:
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def validate_against_schema(
    data: dict[str, Any],
    schema: dict[str, Any],
    *,
    enums: dict[str, list[str]] | None = None,
    require_optional: bool = False,
) -> list[ValidationIssue]:
    enums = enums or load_enums()
    issues: list[ValidationIssue] = []
    required = [str(item) for item in schema.get("required", [])]
    fields = schema.get("fields", {}) if isinstance(schema.get("fields"), dict) else {}

    for field in required:
        value = data.get(field)
        if value is None or value == "" or value == []:
            issues.append(ValidationIssue(field, "missing required field"))

    for field, value in data.items():
        spec = fields.get(field)
        if not isinstance(spec, dict):
            continue
        field_type = str(spec.get("type", "string"))
        if field_type == "datetime":
            if value not in (None, "") and not _is_datetime(str(value)):
                issues.append(ValidationIssue(field, "expected ISO-8601 datetime"))
        elif field_type == "enum":
            enum_name = str(spec.get("enum", ""))
            allowed = enums.get(enum_name, [])
            if value not in (None, "") and str(value) not in allowed:
                issues.append(ValidationIssue(field, f"invalid enum value for {enum_name}: {value}"))
        elif field_type == "list":
            if value in (None, ""):
                continue
            if not isinstance(value, list):
                issues.append(ValidationIssue(field, "expected list"))
                continue
            item_type = str(spec.get("item_type", "string"))
            for index, item in enumerate(value):
                if item_type == "path" and not _is_safe_rel_path(str(item)):
                    issues.append(ValidationIssue(field, f"unsafe path at index {index}: {item}"))

    if require_optional:
        for field in schema.get("optional", []):
            if field not in data or data.get(field) in (None, "", []):
                issues.append(ValidationIssue(str(field), "missing optional field under strict mode", level="warning"))

    return issues


def parse_expires_at(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def issues_to_messages(issues: list[ValidationIssue]) -> list[str]:
    return [f"{item.field}: {item.message}" for item in issues if item.level == "error"]


def frontmatter_errors_to_issues(errors: list[FrontmatterError]) -> list[ValidationIssue]:
    return [ValidationIssue("frontmatter", f"line {err.line}: {err.message}") for err in errors]
