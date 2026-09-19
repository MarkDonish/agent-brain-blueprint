"""Vault layout contract and read-only layout detection.

The public blueprint uses an English directory vocabulary while the local
Agent-Brain uses a Chinese one. Callers must resolve one :class:`VaultLayout`
before constructing paths; they must not guess based on individual files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = REPO_ROOT / "schemas" / "vault_layout.json"


class VaultLayoutError(ValueError):
    """Raised when a vault has no unique supported layout."""


# Descriptive alias for callers/tests that name this failure a detection error.
LayoutDetectionError = VaultLayoutError


@dataclass(frozen=True)
class VaultLayout:
    """Immutable view of one configured vault layout."""

    layout_id: str
    paths: tuple[dict[str, Any], ...]
    project_paths: tuple[dict[str, Any], ...]
    slots: Mapping[str, str]
    index_files: Mapping[str, str]
    markers: tuple[dict[str, Any], ...]
    project_activation: str
    localized_enum_fields: Mapping[str, tuple[str, ...]]

    @property
    def id(self) -> str:
        """Short alias useful to adapters that call the identifier ``id``."""

        return self.layout_id

    @property
    def project_root_rel(self) -> str:
        return self.projects_root_rel

    @property
    def claims_dir_rel(self) -> str:
        return self.claims_root_rel

    def __getitem__(self, key: str) -> Any:
        """Expose stable mapping-style fields without making the object mutable."""

        if key in {"id", "layout", "layout_id"}:
            return self.layout_id
        if key in self.slots:
            return self.slots[key]
        if key in {
            "paths",
            "project_paths",
            "markers",
            "slots",
            "index_files",
            "project_activation",
            "localized_enum_fields",
        }:
            return getattr(self, key)
        raise KeyError(key)

    @property
    def projects_root_rel(self) -> str:
        return self.slots["projects_root"]

    @property
    def claims_root_rel(self) -> str:
        return self.slots["claims_root"]

    @property
    def entrypoint_rel(self) -> str:
        return self.slots["entrypoint"]

    @property
    def retrieval_root_rel(self) -> str:
        return self.slots.get("retrieval_root", "50_retrieval")

    def relative_path(self, slot: str) -> str:
        """Return a root-relative path for a logical slot."""

        aliases = {
            "project_overview": "overview",
            "current_task": "current_work",
            "current_work_dir": "current_work",
            "handoff": "handoffs",
            "handoff_dir": "handoffs",
            "validation_dir": "validation",
            "decision_dir": "decisions",
            "summary_dir": "summaries",
            "raw_source_dir": "raw_sources",
            "projects": "projects_root",
            "claims": "claims_root",
            "entrypoint_card": "entrypoint",
        }
        key = aliases.get(slot, slot)
        try:
            return str(self.slots[key])
        except KeyError as exc:
            raise VaultLayoutError(
                f"layout {self.layout_id!r} has no logical slot {slot!r}"
            ) from exc

    def path(self, root: Path, slot: str) -> Path:
        """Resolve a root-level logical slot under ``root``."""

        return root.expanduser().resolve() / self.relative_path(slot)

    def project_relative_path(self, project: str, slot: str) -> str:
        """Return ``<projects-root>/<project>/<slot>`` as a POSIX path."""

        _validate_project_component(project)
        return "/".join((self.projects_root_rel, project, self.relative_path(slot)))

    def project_path(self, root: Path, project: str, slot: str) -> Path:
        """Resolve a project logical slot under ``root``."""

        return root.expanduser().resolve() / self.project_relative_path(project, slot)

    def project_dir(self, root: Path, project: str) -> Path:
        """Resolve a project directory under this layout."""

        _validate_project_component(project)
        return root.expanduser().resolve() / self.projects_root_rel / project

    def project_index_relative_path(self, project: str, slot: str) -> str:
        """Return the conventional index path for a project section."""

        _validate_project_component(project)
        filename = self.index_files.get(slot) or self.index_files.get(
            {"current_task": "current_work", "handoff": "handoffs"}.get(slot, slot),
            "INDEX.md",
        )
        return "/".join((self.projects_root_rel, project, self.relative_path(slot), filename))

    def project_index_path(self, root: Path, project: str, slot: str) -> Path:
        """Resolve a conventional project section index under ``root``."""

        return root.expanduser().resolve() / self.project_index_relative_path(project, slot)

    def required_entries(self, *, project: bool = False) -> list[dict[str, Any]]:
        entries = self.project_paths if project else self.paths
        return [dict(entry) for entry in entries if entry.get("required", True)]

    def relaxed_enum_fields(self, schema_name: str) -> frozenset[str]:
        """Return localized descriptive enum fields for one record schema.

        Operational state-machine fields are intentionally absent from this
        allowlist and therefore remain strict in every layout.
        """

        return frozenset(self.localized_enum_fields.get(schema_name, ()))


def _validate_project_component(project: str) -> None:
    raw = str(project)
    if (
        not raw
        or raw != raw.strip()
        or raw in {".", ".."}
        or "/" in raw
        or "\\" in raw
        or ".." in raw
        or any(ord(ch) < 32 for ch in raw)
    ):
        raise VaultLayoutError(f"invalid project name for layout path: {project!r}")


@lru_cache(maxsize=1)
def load_vault_layout() -> dict[str, Any]:
    """Load the JSON layout contract."""

    try:
        return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VaultLayoutError(f"cannot load vault layout schema: {LAYOUT_PATH.name}") from exc


def _entries(raw: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("path") or not item.get("kind"):
            continue
        out.append(
            {
                "path": str(item["path"]),
                "kind": str(item["kind"]),
                "required": bool(item.get("required", True)),
            }
        )
    return tuple(out)


@lru_cache(maxsize=1)
def supported_layouts() -> tuple[VaultLayout, ...]:
    """Return all configured layout contracts in schema order."""

    raw = load_vault_layout()
    layouts = raw.get("layouts")
    if not isinstance(layouts, dict) or not layouts:
        # Compatibility with pre-adapter schema files: treat old top-level
        # lists as the English blueprint contract.
        layouts = {
            "blueprint-en-v1": {
                "paths": raw.get("paths", []),
                "project_paths": raw.get("project_paths", []),
                "markers": [
                    {"path": "AGENTS.md", "kind": "file"},
                    {"path": "10_projects", "kind": "directory"},
                ],
                "slots": {
                    "entrypoint": "00_entrypoint/SESSION_START_CARD.md",
                    "projects_root": "10_projects",
                    "global_decisions": "30_global_decisions",
                    "claims_root": "40_handoffs/session_claims",
                    "retrieval_root": "50_retrieval",
                    "overview": "PROJECT_OVERVIEW.md",
                    "current_work": "10_current_work",
                    "handoffs": "20_handoffs",
                    "docs": "30_docs",
                    "validation": "40_validation",
                    "decisions": "50_decisions",
                    "summaries": "60_summaries",
                    "raw_sources": "90_raw_sources",
                },
                "index_files": {slot: "INDEX.md" for slot in (
                    "current_work", "handoffs", "docs", "validation",
                    "decisions", "summaries", "raw_sources"
                )},
                "project_activation": "directory",
                "localized_enum_fields": {},
            }
        }

    result: list[VaultLayout] = []
    for layout_id, item in layouts.items():
        if not isinstance(item, dict):
            continue
        slots_raw = item.get("slots")
        slots = (
            {str(key): str(value) for key, value in slots_raw.items()}
            if isinstance(slots_raw, dict)
            else {}
        )
        if not slots.get("projects_root") or not slots.get("entrypoint"):
            continue
        index_raw = item.get("index_files")
        index_files = (
            {str(key): str(value) for key, value in index_raw.items()}
            if isinstance(index_raw, dict)
            else {}
        )
        localized_raw = item.get("localized_enum_fields")
        localized_enum_fields = (
            {
                str(schema_name): tuple(str(field) for field in fields)
                for schema_name, fields in localized_raw.items()
                if isinstance(fields, list)
            }
            if isinstance(localized_raw, dict)
            else {}
        )
        paths = _entries(item.get("paths"))
        project_paths = _entries(item.get("project_paths"))
        markers = _entries(item.get("markers"))
        if not markers:
            markers = tuple(
                entry
                for entry in paths
                if entry["path"] in {slots.get("projects_root"), slots.get("entrypoint")}
            )
        result.append(
            VaultLayout(
                layout_id=str(layout_id),
                paths=paths,
                project_paths=project_paths,
                slots=slots,
                index_files=index_files,
                markers=markers,
                project_activation=str(item.get("project_activation", "directory")),
                localized_enum_fields=localized_enum_fields,
            )
        )
    if not result:
        raise VaultLayoutError("vault layout schema defines no usable layouts")
    return tuple(result)


def _candidate_markers(root: Path, layout: VaultLayout) -> list[str]:
    # Only mutually exclusive core vocabulary identifies a layout.  Auxiliary
    # markers such as ``AGENTS.md``, ``.agent-brain`` and the derived retrieval
    # directory may be present in either vault (for example after migration),
    # so they must not create a false English/Chinese conflict.  Presence (even
    # with the wrong kind) is still enough for a core marker so the structure
    # checker can report an actionable type mismatch.
    core_paths = {layout.projects_root_rel, layout.entrypoint_rel}
    return [
        str(entry["path"])
        for entry in layout.markers
        if str(entry["path"]) in core_paths
        and (root / str(entry["path"])).exists()
    ]


def detect_layout(root: Path, *, strict: bool = False) -> VaultLayout:
    """Detect a unique supported layout, failing closed on ambiguity.

    A partial but unambiguous vault is accepted so lightweight temporary
    callers continue to work; the structure checker reports missing entries.
    """

    root = root.expanduser().resolve()
    if not root.is_dir():
        raise VaultLayoutError(f"vault root is not a directory: {root.name or '.'}")

    candidates: list[tuple[VaultLayout, list[str]]] = []
    for layout in supported_layouts():
        markers = _candidate_markers(root, layout)
        if markers:
            candidates.append((layout, markers))

    if len(candidates) == 1:
        return candidates[0][0]
    if not candidates:
        known = ", ".join(layout.layout_id for layout in supported_layouts())
        mode = " (strict)" if strict else ""
        raise VaultLayoutError(
            f"unable to detect supported vault layout{mode}; expected one of: {known}"
        )

    detail = "; ".join(
        f"{layout.layout_id}: {', '.join(markers)}" for layout, markers in candidates
    )
    raise VaultLayoutError(
        "ambiguous vault layout; conflicting core markers detected — " + detail
    )


# Readable aliases for downstream adapters.
resolve_layout = detect_layout
layout_for_vault = detect_layout
detect_vault_layout = detect_layout
get_vault_layout = detect_layout
select_layout = detect_layout


def required_entries(
    *,
    project: bool = False,
    layout: VaultLayout | str | None = None,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Return required entries for a selected layout.

    With no selector this preserves the historical English default. Passing
    ``root`` selects its detected layout and is preferred for read-only checks.
    """

    selected: VaultLayout
    if isinstance(layout, VaultLayout):
        selected = layout
    elif isinstance(layout, str):
        matches = [item for item in supported_layouts() if item.layout_id == layout]
        if not matches:
            raise VaultLayoutError(f"unsupported vault layout: {layout!r}")
        selected = matches[0]
    elif root is not None:
        selected = detect_layout(root)
    else:
        default_id = str(load_vault_layout().get("default_layout") or "blueprint-en-v1")
        selected = next(
            (item for item in supported_layouts() if item.layout_id == default_id),
            supported_layouts()[0],
        )
    return selected.required_entries(project=project)


def record_type_from_path(rel: str, *, data: Mapping[str, Any] | None = None) -> str:
    """Classify a record path using both supported vocabularies."""

    metadata = data or {}
    explicit = metadata.get("record_type")
    if explicit:
        return str(explicit)
    memory_type = str(metadata.get("memory_type") or "")
    mapping = {
        "decision": "decision",
        "validation": "validation",
        "handoff": "handoff",
        "session-handoff": "claim",
        "task": "task",
        "fact": "memory",
        "lesson": "memory",
        "workflow": "memory",
        "evidence": "memory",
    }
    if memory_type in mapping:
        return mapping[memory_type]

    rel_n = rel.replace("\\", "/")
    parts = rel_n.split("/")
    dirs = set(parts[:-1])
    if "session_claims" in dirs or "会话认领" in dirs:
        return "claim"
    if {"50_decisions", "50_事实与决策", "30_global_decisions", "30_全局事实与决策"} & dirs:
        return "decision"
    if {"40_validation", "40_验证记录"} & dirs:
        return "validation"
    if {"20_handoffs", "20_交接记录"} & dirs:
        return "handoff"
    if {"10_current_work", "10_当前任务"} & dirs:
        return "task"
    if {"60_summaries", "60_会话摘要"} & dirs or parts[-1] in {
        "PROJECT_OVERVIEW.md",
        "00_项目总览.md",
    }:
        return "summary"
    if {"90_raw_sources", "90_原始材料索引"} & dirs:
        return "source"
    return "memory"


def project_from_path(rel: str) -> str:
    """Extract project name from either supported project-root segment."""

    parts = rel.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] in {"10_projects", "10_项目工作区"}:
        return parts[1]
    return ""


def layout_ignored_dir_names(layout: VaultLayout | None = None) -> set[str]:
    """Return cache/sensitive directory names excluded from retrieval."""

    names = {
        ".git",
        ".venv",
        "__pycache__",
        "indexes",
        "cache",
        "logs",
        "data",
        "private",
        "80_sensitive_isolation",
        "80_敏感隔离_不要放进来",
        "90_archive",
        "90_归档",
        "node_modules",
    }
    return names


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
