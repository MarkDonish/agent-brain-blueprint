#!/usr/bin/env python3
"""Strict YAML-subset frontmatter parser with line-level errors.

Supported subset (no third-party dependency):
- key: value scalars (string / bool / int / float / null)
- key: with following indented list items "- value"
- quoted strings with " or '
- comments starting with #
- duplicate keys are errors
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrontmatterError:
    line: int
    message: str


@dataclass
class FrontmatterResult:
    data: dict[str, Any]
    errors: list[FrontmatterError]
    body: str
    start_line: int = 1

    @property
    def error_messages(self) -> list[str]:
        return [f"line {item.line}: {item.message}" for item in self.errors]


_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")
_LIST_RE = re.compile(r"^\s*-\s*(.*)$")


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def parse_frontmatter(text: str) -> FrontmatterResult:
    """Parse leading YAML frontmatter delimited by --- lines."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return FrontmatterResult(data={}, errors=[FrontmatterError(1, "missing frontmatter")], body=text)

    lines = text.splitlines()
    # Find closing ---
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return FrontmatterResult(data={}, errors=[FrontmatterError(1, "unterminated frontmatter")], body=text)

    data: dict[str, Any] = {}
    errors: list[FrontmatterError] = []
    current_list_key: str | None = None

    for offset, raw in enumerate(lines[1:end_index], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        list_match = _LIST_RE.match(raw)
        if list_match and current_list_key is not None:
            data.setdefault(current_list_key, [])
            if not isinstance(data[current_list_key], list):
                errors.append(FrontmatterError(offset, f"list item under non-list key: {current_list_key}"))
                continue
            data[current_list_key].append(_parse_scalar(list_match.group(1)))
            continue

        key_match = _KEY_RE.match(raw.strip())
        if not key_match:
            errors.append(FrontmatterError(offset, f"malformed frontmatter line: {raw}"))
            current_list_key = None
            continue

        key, value = key_match.groups()
        if key in data:
            errors.append(FrontmatterError(offset, f"duplicate field: {key}"))
            current_list_key = None
            continue

        if value.strip() == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = _parse_scalar(value)
            current_list_key = None

    body = "\n".join(lines[end_index + 1 :])
    if text.endswith("\n") and body and not body.endswith("\n"):
        body += "\n"
    return FrontmatterResult(data=data, errors=errors, body=body, start_line=1)


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") or text.startswith("---\r\n")
