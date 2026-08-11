"""Scan vault Markdown into indexable record dicts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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

# Paths that are operational indexes, not durable knowledge to rank highly.
LOW_PRIORITY_GLOBS = (
    "60_templates/",
    "00_entrypoint/",
    "20_agent_catalog/",
    "50_retrieval/",
    "70_inbox/",
    "90_archive/",
)


def _project_from_path(rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "10_projects":
        return parts[1]
    return ""


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
    if data.get("record_type"):
        return str(data["record_type"])
    mt = str(data.get("memory_type") or "")
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
    if mt in mapping:
        return mapping[mt]
    rel_n = rel.replace("\\", "/")
    if "/50_decisions/" in rel_n:
        return "decision"
    if "/40_validation/" in rel_n:
        return "validation"
    if "/20_handoffs/" in rel_n:
        return "handoff"
    if "session_claims/" in rel_n:
        return "claim"
    if rel_n.endswith("PROJECT_OVERVIEW.md"):
        return "summary"
    if "/10_current_work/" in rel_n:
        return "task"
    return "memory"


def iter_markdown_files(vault: Path):
    vault = vault.resolve()
    for path in sorted(vault.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(vault)
        except ValueError:
            continue
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        yield path, str(rel).replace("\\", "/")


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
        # Skip pure directory stubs with almost no content
        if path.name in {"README.md", "INDEX.md", ".gitkeep"} and len(body.strip()) < 40 and not data.get("title"):
            # still index INDEX with some content
            if path.name == "README.md" and len(body.strip()) < 80:
                continue

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
