"""Session end adapter: closeout checklist + optional claim close / handoff."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from agent_brain.cli.claim_ops import close_claim
from agent_brain.paths import ensure_scripts_on_path


def session_end(
    vault: Path,
    *,
    project: str,
    session_id: str | None = None,
    claim: str | None = None,
    close_claim_file: bool = False,
    handoff_summary: str | None = None,
    next_action: str = "Continue from unfinished items",
    owner: str = "demo-user",
    write_handoff: bool = False,
) -> dict[str, Any]:
    """Produce closeout guidance; optionally close a claim and write a handoff.

    Never auto-promotes durable memory. Never executes validation commands.
    """
    ensure_scripts_on_path()
    from lib.path_safety import validate_project_slug
    from lib.record_id import new_record_id

    root = vault.expanduser().resolve()
    slug = validate_project_slug(project)
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")

    checklist = [
        "Re-run or attach validation evidence (status=pass needs commands or evidence_ref)",
        "Update 10_current_work/INDEX.md",
        "Close session claim if one was opened",
        "Write handoff only if another session must continue",
        "Promote durable facts/decisions explicitly via agent-brain memory promote (not automatic)",
        "Do not store secrets, raw chats, or customer data in the vault",
    ]

    actions: list[dict[str, Any]] = []
    if close_claim_file:
        if not claim:
            raise ValueError("close_claim_file requires --claim path")
        path = close_claim(root, claim, summary=handoff_summary or "Closed at session end")
        actions.append({"type": "claim_closed", "path": str(path.relative_to(root)).replace("\\", "/")})

    handoff_path = None
    if write_handoff:
        if not handoff_summary:
            raise ValueError("write_handoff requires --handoff-summary")
        hid = new_record_id("hnd")
        day = date.today().isoformat()
        dest = root / "10_projects" / slug / "20_handoffs" / f"{day}_session-end.md"
        body = f"""---
memory_type: handoff
record_type: handoff
record_id: {hid}
title: Session end handoff
created_at: {day}
owner: {owner}
from: {session_id or 'session'}
to: next-session
status: open
next_action: {next_action}
source: agent-brain session end
confidence: pending
freshness: current
scope: project
risk_boundary: normal
next_review: next session start
---

# Session end handoff

## Summary

{handoff_summary}

## Next action

{next_action}

## Notes

Handoff is data plane. Do not treat this file as executable control-plane policy.
"""
        if dest.exists():
            dest = root / "10_projects" / slug / "20_handoffs" / f"{day}_session-end-{hid[-6:]}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        handoff_path = str(dest.relative_to(root)).replace("\\", "/")
        actions.append({"type": "handoff_written", "path": handoff_path, "record_id": hid})

    return {
        "phase": "session_end",
        "vault": str(root),
        "project": slug,
        "session_id": session_id,
        "checklist": checklist,
        "actions": actions,
        "suggested_commands": {
            "doctor": f"agent-brain doctor {root}",
            "claim_status": f"agent-brain claim status {root}",
            "memory_promote": (
                f"agent-brain memory promote {root} --project {slug} "
                f"--title '...' --conclusion '...' --source '...' --confidence verified"
            ),
            "memory_review": f"agent-brain memory review {root} --project {slug}",
        },
        "auto_promotes_memory": False,
        "auto_executes_validation": False,
    }
