"""Public import surface for the shared vault layout adapter."""

from __future__ import annotations

from agent_brain.paths import ensure_scripts_on_path

ensure_scripts_on_path()

from lib.vault_layout import (  # noqa: E402
    LayoutDetectionError,
    VaultLayout,
    VaultLayoutError,
    detect_layout,
    detect_vault_layout,
    get_vault_layout,
    layout_for_vault,
    layout_ignored_dir_names,
    load_vault_layout,
    project_from_path,
    record_type_from_path,
    required_entries,
    resolve_layout,
    select_layout,
    supported_layouts,
)

__all__ = [
    "LayoutDetectionError",
    "VaultLayout",
    "VaultLayoutError",
    "detect_layout",
    "detect_vault_layout",
    "get_vault_layout",
    "layout_for_vault",
    "layout_ignored_dir_names",
    "load_vault_layout",
    "project_from_path",
    "record_type_from_path",
    "required_entries",
    "resolve_layout",
    "select_layout",
    "supported_layouts",
]
