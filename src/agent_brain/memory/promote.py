"""Promote a durable memory/decision into the vault (explicit, not automatic)."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from agent_brain.paths import ensure_scripts_on_path

PROMOTE_ALLOWED_MEMORY_TYPES = frozenset(
    {"decision", "fact", "workflow", "lesson", "evidence"}
)
PROMOTE_BLOCKED_HINTS = (
    "temporary speculation",
    "raw conversation",
    "debugging only",
)


def _slug(title: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return (raw or "memory")[:60]


def _iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def promote_memory(
    vault: Path,
    *,
    project: str | None,
    title: str,
    conclusion: str,
    source: str,
    owner: str = "demo-user",
    memory_type: str = "decision",
    knowledge_type: str | None = None,
    confidence: str = "verified",
    freshness: str = "current",
    scope: str | None = None,
    risk_boundary: str = "normal",
    next_review: str | None = None,
    review_after: str | None = None,
    source_path_or_url: str = "",
    global_decision: bool = False,
    dry_run: bool = False,
    filename: str | None = None,
) -> dict[str, Any]:
    """Write a governed durable record. Returns metadata; never auto-trusts inference.

    Rejects production risk without confidence=verified.
    Does not promote from free-form chat dumps — caller must supply structured fields.
    """
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, project_dir, validate_project_slug
    from lib.record_id import new_record_id
    from lib.schema import load_enums, load_schema, validate_against_schema

    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")

    title = title.strip()
    conclusion = conclusion.strip()
    source = source.strip()
    if not title or not conclusion or not source:
        raise ValueError("title, conclusion, and source are required")
    if memory_type not in PROMOTE_ALLOWED_MEMORY_TYPES:
        raise ValueError(
            f"memory_type {memory_type!r} not allowed for promote; "
            f"allowed={sorted(PROMOTE_ALLOWED_MEMORY_TYPES)}"
        )
    if risk_boundary == "production" and confidence != "verified":
        raise ValueError("production risk_boundary requires confidence=verified")
    for hint in PROMOTE_BLOCKED_HINTS:
        if hint in conclusion.lower():
            raise ValueError(f"refusing promote: content looks like {hint!r}")

    if global_decision:
        dest_dir = root / "30_global_decisions"
        scope_val = scope or "global"
        project_slug = None
    else:
        if not project:
            raise ValueError("project is required unless --global")
        project_slug = validate_project_slug(project)
        dest_dir = project_dir(root, project_slug) / "50_decisions"
        scope_val = scope or "project"

    record_id = new_record_id("mem")
    created = _iso_date()
    from datetime import timedelta

    nr = next_review or (date.today() + timedelta(days=30)).isoformat()
    ra = review_after or nr
    kt = knowledge_type or ("decision" if memory_type == "decision" else "fact")
    record_type = "decision" if memory_type == "decision" else "memory"

    data = {
        "memory_type": memory_type,
        "record_type": record_type,
        "knowledge_type": kt,
        "record_id": record_id,
        "title": title,
        "created_at": created,
        "updated_at": created,
        "state": "active",
        "source": source,
        "source_path_or_url": source_path_or_url or source,
        "confidence": confidence,
        "freshness": freshness,
        "scope": scope_val,
        "risk_boundary": risk_boundary,
        "next_review": nr,
        "review_after": ra,
        "owner": owner,
    }
    issues = validate_against_schema(data, load_schema("memory_record"), enums=load_enums())
    errors = [f"{i.field}: {i.message}" for i in issues if i.level == "error"]
    if errors:
        raise ValueError("schema validation failed: " + "; ".join(errors))

    if filename is None:
        filename = f"{created}_{_slug(title)}.md"
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise PathSafetyError(f"unsafe filename: {filename}")
    path = dest_dir / filename
    if path.exists():
        raise FileExistsError(f"record already exists: {path}")

    body = f"""---
memory_type: {memory_type}
record_type: {record_type}
knowledge_type: {kt}
record_id: {record_id}
title: {title}
created_at: {created}
updated_at: {created}
state: active
source: {source}
source_path_or_url: {data['source_path_or_url']}
confidence: {confidence}
freshness: {freshness}
scope: {scope_val}
risk_boundary: {risk_boundary}
next_review: {nr}
review_after: {ra}
owner: {owner}
---

# {title}

## Conclusion

{conclusion}

## Evidence

- Source: `{data['source_path_or_url']}`
- Evidence status: {confidence}
- Note: promotion is explicit; this record is not auto-trusted from chat logs.

## Scope and expiry

Scope: `{scope_val}`. Review after `{ra}`. Revalidate before production action.

## Action rule

Treat as durable only while freshness remains current and state is active.
"""

    rel = str(path.relative_to(root)).replace("\\", "/")
    result = {
        "action": "promote",
        "dry_run": dry_run,
        "path": rel,
        "absolute_path": str(path),
        "record_id": record_id,
        "project": project_slug,
        "memory_type": memory_type,
        "confidence": confidence,
        "state": "active",
        "auto_trusted": False,
    }
    if dry_run:
        result["body_preview"] = body[:500]
        return result

    dest_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return result
