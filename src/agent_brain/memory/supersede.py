"""Supersede an active durable record with a new one."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from agent_brain.memory.frontmatter_edit import set_frontmatter_fields
from agent_brain.memory.promote import promote_memory
from agent_brain.paths import ensure_scripts_on_path


def find_record_by_id(vault: Path, record_id: str) -> Path | None:
    ensure_scripts_on_path()
    from lib.frontmatter import parse_frontmatter

    vault = vault.expanduser().resolve()
    rid = record_id.strip()
    if not rid:
        return None
    for path in vault.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(vault)
        except ValueError:
            continue
        if any(p in {"indexes", ".git", "80_sensitive_isolation"} for p in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if f"record_id: {rid}" not in text and f"record_id:{rid}" not in text:
            # fast path miss
            if rid not in text:
                continue
        parsed = parse_frontmatter(text)
        if str(parsed.data.get("record_id") or "") == rid:
            return path
    return None


def supersede_memory(
    vault: Path,
    *,
    old_record_id: str,
    title: str,
    conclusion: str,
    source: str,
    owner: str = "demo-user",
    confidence: str = "verified",
    risk_boundary: str = "normal",
    project: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Mark old record superseded and promote a replacement that supersedes it."""
    root = vault.expanduser().resolve()
    old_path = find_record_by_id(root, old_record_id)
    if old_path is None:
        raise FileNotFoundError(f"record_id not found: {old_record_id}")

    # Infer project from path if not provided
    rel = str(old_path.relative_to(root)).replace("\\", "/")
    global_decision = rel.startswith("30_global_decisions/")
    if not global_decision and project is None:
        parts = rel.split("/")
        if len(parts) >= 2 and parts[0] == "10_projects":
            project = parts[1]
        else:
            raise ValueError("could not infer project; pass --project")

    if dry_run:
        return {
            "action": "supersede",
            "dry_run": True,
            "old_record_id": old_record_id,
            "old_path": rel,
            "would_set_old_state": "superseded",
            "would_promote_title": title,
        }

    text = old_path.read_text(encoding="utf-8")
    updated = set_frontmatter_fields(
        text,
        {
            "state": "superseded",
            "freshness": "review-required",
            "updated_at": date.today().isoformat(),
        },
    )
    old_path.write_text(updated, encoding="utf-8")

    promoted = promote_memory(
        root,
        project=project,
        title=title,
        conclusion=conclusion,
        source=source,
        owner=owner,
        confidence=confidence,
        risk_boundary=risk_boundary,
        global_decision=global_decision,
        dry_run=False,
    )

    # Attach supersedes on the new record
    new_path = Path(promoted["absolute_path"])
    new_text = new_path.read_text(encoding="utf-8")
    new_text = set_frontmatter_fields(new_text, {"supersedes": [old_record_id]})
    # also add body note
    if "## Supersedes" not in new_text:
        new_text = new_text.rstrip() + f"\n\n## Supersedes\n\n- `{old_record_id}` (`{rel}`)\n"
    new_path.write_text(new_text, encoding="utf-8")

    return {
        "action": "supersede",
        "dry_run": False,
        "old_record_id": old_record_id,
        "old_path": rel,
        "old_state": "superseded",
        "new_record_id": promoted["record_id"],
        "new_path": promoted["path"],
        "auto_trusted": False,
    }
