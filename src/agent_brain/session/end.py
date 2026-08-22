"""Session end adapter: closeout checklist + optional claim close / handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_brain.cli.claim_ops import close_claim
from agent_brain.handoff.engine import create_handoff
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
    completed_tasks: list[str] | str | None = None,
    evidence: list[dict[str, str] | str] | str | None = None,
    active_decisions: list[str] | str | None = None,
    superseded_decisions: list[dict[str, str] | str] | str | None = None,
    next_steps: list[str] | str | None = None,
    blockers: list[str] | str | None = None,
    owner: str = "demo-user",
    write_handoff: bool = False,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Produce closeout guidance; optionally close a claim and write a handoff.

    Never auto-promotes durable memory. Never executes validation commands.
    """
    ensure_scripts_on_path()
    from lib.path_safety import validate_project_slug

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

    if write_handoff:
        if not handoff_summary:
            raise ValueError("write_handoff requires --handoff-summary")
        all_steps = [next_action] if next_action else []
        if next_steps:
            if isinstance(next_steps, list):
                all_steps.extend(next_steps)
            else:
                all_steps.append(str(next_steps))
        
        h_res = create_handoff(
            root,
            project=slug,
            summary=handoff_summary,
            session_id=session_id,
            completed_tasks=completed_tasks,
            evidence=evidence,
            active_decisions=active_decisions,
            superseded_decisions=superseded_decisions,
            next_steps=all_steps,
            blockers=blockers,
            claim=claim if close_claim_file else None,
            close_claim_file=close_claim_file,
            owner=owner,
        )
        actions.append({"type": "handoff_written", "path": h_res["path"], "record_id": h_res["record_id"]})
        if h_res.get("closed_claims"):
            for cp in h_res["closed_claims"]:
                actions.append({"type": "claim_closed", "path": cp})
    elif close_claim_file:
        if not claim:
            raise ValueError("close_claim_file requires --claim path")
        path = close_claim(root, claim, summary=handoff_summary or "Closed at session end")
        actions.append({"type": "claim_closed", "path": str(path.relative_to(root)).replace("\\", "/")})

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
