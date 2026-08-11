"""Vault format version constants and manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Tool release that introduced vault_format_version 1.
TOOL_VERSION = "0.5.0"
VAULT_FORMAT_VERSION = 1
SUPPORTED_VAULT_FORMAT_VERSIONS = frozenset({1})

MANIFEST_REL = ".agent-brain/manifest.json"


def default_manifest(*, created_with: str | None = None) -> dict[str, Any]:
    return {
        "vault_format_version": VAULT_FORMAT_VERSION,
        "created_with": created_with or TOOL_VERSION,
        "minimum_tool_version": TOOL_VERSION,
        "layout_schema": "schemas/vault_layout.json",
    }


def manifest_path(vault_root: Path) -> Path:
    return vault_root / ".agent-brain" / "manifest.json"


def write_manifest(vault_root: Path, *, created_with: str | None = None) -> Path:
    path = manifest_path(vault_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = default_manifest(created_with=created_with)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_manifest(vault_root: Path) -> dict[str, Any] | None:
    path = manifest_path(vault_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifest(data: dict[str, Any] | None) -> list[str]:
    if data is None:
        return ["missing vault manifest (.agent-brain/manifest.json)"]
    errors: list[str] = []
    version = data.get("vault_format_version")
    if not isinstance(version, int):
        errors.append("vault_format_version must be an integer")
    elif version not in SUPPORTED_VAULT_FORMAT_VERSIONS:
        errors.append(
            f"unsupported vault_format_version {version}; "
            f"supported={sorted(SUPPORTED_VAULT_FORMAT_VERSIONS)}"
        )
    if "created_with" not in data:
        errors.append("created_with is required")
    if "minimum_tool_version" not in data:
        errors.append("minimum_tool_version is required")
    return errors
