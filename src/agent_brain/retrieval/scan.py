"""Scan vault Markdown into indexable record dicts."""

from __future__ import annotations

import hashlib

from pathlib import Path
from typing import Any

from agent_brain.layout import (
    detect_layout,
    layout_ignored_dir_names,
    project_from_path,
    record_type_from_path,
)
from agent_brain.paths import ensure_scripts_on_path

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "indexes",
    "cache",
    "logs",
    "data",
    "private",
    "80_sensitive_isolation",
    "node_modules",
}


def _blocked_dir_names(layout) -> set[str]:
    """Return directory names that are outside the canonical retrieval plane.

    The scanner historically skipped these directories silently.  Wave 2 keeps
    them out of the index but exposes their Markdown files as ``blocked`` in
    inventory reports so coverage can never be mistaken for whole-vault
    coverage.
    """

    return SKIP_DIR_NAMES | layout_ignored_dir_names(layout)

def _project_from_path(rel: str) -> str:
    normalized = rel.replace("\\", "/")
    parts = normalized.split("/")
    # The layout-level ``10_projects/INDEX.md`` (and its Chinese counterpart)
    # describes the project collection; it is not a project named INDEX.md.
    if len(parts) == 2 and parts[1].lower() in {"index.md", "00_项目索引.md"}:
        return ""
    return project_from_path(rel)


def _title_from(data: dict[str, Any], body: str, path: str) -> str:
    if data.get("title"):
        return str(data["title"]).strip()
    if data.get("task"):
        return str(data["task"]).strip()
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return Path(path).stem


def _record_type(data: dict[str, Any], rel: str) -> str:
    return record_type_from_path(rel, data=data)


def iter_markdown_files(vault: Path):
    vault = vault.resolve()
    layout = detect_layout(vault)
    skip_names = _blocked_dir_names(layout)
    for path in sorted(vault.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(vault)
        except ValueError:
            continue
        if any(part in skip_names for part in rel.parts):
            continue
        yield path, str(rel).replace("\\", "/")


def iter_markdown_inventory(vault: Path):
    """Yield deterministic metadata for eligible and blocked Markdown files.

    Inventory is deliberately independent of frontmatter parsing: source
    coverage is about canonical files on disk, while ``scan_records`` is the
    derived record representation.  Hashes are included so refresh detects a
    content change even when a filesystem preserves a coarse mtime.
    """

    vault = vault.expanduser().resolve()
    layout = detect_layout(vault)
    blocked_names = _blocked_dir_names(layout)
    for path in sorted(vault.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(vault)
        except ValueError:
            continue
        rel_s = str(rel).replace("\\", "/")
        blocked_parts = [part for part in rel.parts if part in blocked_names]
        try:
            stat = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, UnicodeError):
            # An unreadable source cannot be an eligible indexed record.  Keep
            # it visible as blocked rather than silently dropping it.
            blocked_parts = blocked_parts or ["unreadable"]
            stat = None
            digest = ""
        yield {
            "path": rel_s,
            "size": int(stat.st_size) if stat else 0,
            "mtime": float(stat.st_mtime) if stat else 0.0,
            "mtime_ns": int(stat.st_mtime_ns) if stat else 0,
            "fingerprint": digest,
            "blocked": bool(blocked_parts),
            "blocked_reason": ",".join(dict.fromkeys(blocked_parts)),
        }


def source_inventory(vault: Path) -> dict[str, Any]:
    """Return eligible/blocked source inventory used by generation coverage."""

    items = list(iter_markdown_inventory(vault))
    eligible = [item for item in items if not item["blocked"]]
    blocked = [item for item in items if item["blocked"]]
    return {
        "items": items,
        "eligible": eligible,
        "blocked": blocked,
        "source_count": len(eligible),
        "blocked_source_count": len(blocked),
    }


def scan_records(vault: Path) -> list[dict[str, Any]]:
    """Return indexable records. Requires scripts/lib for frontmatter parser."""
    ensure_scripts_on_path()
    from lib.frontmatter import parse_frontmatter

    vault = vault.resolve()
    records: list[dict[str, Any]] = []
    for path, rel in iter_markdown_files(vault):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        parsed = parse_frontmatter(text)
        data = parsed.data if not parsed.errors or text.startswith("---") else {}
        # Index even without perfect frontmatter; body still helps retrieval.
        if parsed.errors and not text.startswith("---"):
            body = text
            data = {}
        else:
            body = parsed.body
        state = str(data.get("state") or "")
        freshness = str(data.get("freshness") or "")
        title = _title_from(data, body, rel)
        record_id = str(data.get("record_id") or f"path:{rel}")
        records.append(
            {
                "record_id": record_id,
                "path": rel,
                "project": _project_from_path(rel),
                "record_type": _record_type(data, rel),
                "memory_type": str(data.get("memory_type") or ""),
                "title": title,
                "body": body.strip(),
                "state": state,
                "freshness": freshness,
                "scope": str(data.get("scope") or ""),
                "risk_boundary": str(data.get("risk_boundary") or ""),
                "updated_at": str(data.get("updated_at") or data.get("created_at") or ""),
                "source_path": rel,
                # Preserve parsed frontmatter for graph relation extraction.
                # Callers should treat it as evidence, never as canonical
                # truth without reopening ``source_path``.
                "metadata": dict(data),
            }
        )
    return records


def is_active_for_context(rec: dict[str, Any]) -> bool:
    state = str(rec.get("state") or "").lower()
    freshness = str(rec.get("freshness") or "").lower()
    if state in {"superseded", "expired", "archived"}:
        return False
    if freshness == "expired":
        return False
    return True


# Descriptive aliases for callers that refer to the coverage input as an
# inventory rather than a scanner.
inventory = source_inventory
scan_inventory = source_inventory
