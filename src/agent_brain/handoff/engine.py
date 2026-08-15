"""Intelligent Session Handoff Engine for multi-agent workflows."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from agent_brain.cli.claim_ops import close_claim
from agent_brain.paths import ensure_scripts_on_path


def _parse_list(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        lines = [line.strip() for line in re.split(r"[\r\n;]+", val) if line.strip()]
        return lines
    return [str(val).strip()]


def _parse_pairs(val: Any) -> list[dict[str, str]]:
    if not val:
        return []
    if isinstance(val, list):
        out = []
        for item in val:
            if isinstance(item, dict):
                k = str(item.get("command") or item.get("decision") or item.get("key") or item.get("name") or "").strip()
                v = str(item.get("result") or item.get("reason") or item.get("value") or item.get("status") or "").strip()
                if k:
                    out.append({"key": k, "value": v})
            elif isinstance(item, str) and item.strip():
                parts = re.split(r"::|->|=>", item, maxsplit=1)
                if len(parts) == 2:
                    out.append({"key": parts[0].strip(), "value": parts[1].strip()})
                else:
                    out.append({"key": item.strip(), "value": "PASS"})
        return out
    if isinstance(val, str):
        return _parse_pairs(_parse_list(val))
    return []


def create_handoff(
    vault: Path,
    *,
    project: str,
    summary: str,
    session_id: str | None = None,
    completed_tasks: list[str] | str | None = None,
    evidence: list[dict[str, str] | str] | str | None = None,
    active_decisions: list[str] | str | None = None,
    superseded_decisions: list[dict[str, str] | str] | str | None = None,
    next_steps: list[str] | str | None = None,
    blockers: list[str] | str | None = None,
    claim: str | None = None,
    close_claim_file: bool = True,
    owner: str = "agent",
    status: str = "open",
    to_agent: str = "next-session",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a structured, source-backed handoff card and optionally close active claims."""
    ensure_scripts_on_path()
    from lib.frontmatter import parse_frontmatter
    from lib.path_safety import safe_vault_join, validate_project_slug
    from lib.record_id import new_record_id

    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")

    slug = validate_project_slug(project)
    if not summary or not summary.strip():
        raise ValueError("handoff summary is required")

    clean_summary = summary.strip()
    tasks = _parse_list(completed_tasks)
    evidence_list = _parse_pairs(evidence)
    active_decs = _parse_list(active_decisions)
    superseded_decs = _parse_pairs(superseded_decisions)
    steps = _parse_list(next_steps)
    blocker_list = _parse_list(blockers)

    # Detect handoffs directory (Dual layout support)
    chinese_proj = safe_vault_join(root, "10_项目工作区", slug)
    if chinese_proj.is_dir():
        handoff_dir = safe_vault_join(root, "10_项目工作区", slug, "20_交接记录")
    else:
        handoff_dir = safe_vault_join(root, "10_projects", slug, "20_handoffs")

    hid = new_record_id("hnd")
    day = date.today().isoformat()

    first_next = steps[0] if steps else "Continue from project roadmap"

    # Build Markdown
    lines: list[str] = [
        "---",
        "memory_type: handoff",
        "record_type: handoff",
        f"record_id: {hid}",
        f"title: {slug} · Session Handoff",
        f"created_at: {day}",
        f"owner: {owner}",
        f"from: {session_id or owner}",
        f"to: {to_agent}",
        f"status: {status}",
        f"next_action: {first_next}",
        "source: agent-brain intelligent handoff",
        "confidence: verified",
        "freshness: current",
        "scope: project",
        "risk_boundary: normal",
        "next_review: next session start",
        "---",
        "",
        f"# {slug} · Session Handoff",
        "",
        f"**Date**: {day}  ",
        f"**Session ID**: `{session_id or 'adhoc'}`  ",
        f"**From**: `{owner}` ➡️ **To**: `{to_agent}`  ",
        "",
        "---",
        "",
        "## 1. 🎯 30-Second Status & Summary",
        "",
        clean_summary,
        "",
    ]

    if tasks:
        lines.extend([
            "---",
            "",
            "## 2. 📦 Completed Tasks & Verified Work",
            "",
        ])
        for t in tasks:
            lines.append(f"- [x] {t}")
        lines.append("")

    if evidence_list:
        lines.extend([
            "---",
            "",
            "## 3. 🧪 Fresh Validation Evidence (Audit Trail)",
            "",
            "| # | Command / Verification Check | Result / Status |",
            "|---|------------------------------|-----------------|",
        ])
        for i, item in enumerate(evidence_list, 1):
            cmd = item["key"].replace("|", "\\|")
            res = item["value"].replace("|", "\\|")
            lines.append(f"| {i} | `{cmd}` | {res} |")
        lines.append("")

    if active_decs or superseded_decs:
        lines.extend([
            "---",
            "",
            "## 4. 🔄 Decisions & Rule Lineage",
            "",
        ])
        if active_decs:
            lines.append("### Active Decisions")
            for d in active_decs:
                lines.append(f"- ✅ **[Active]** {d}")
            lines.append("")
        if superseded_decs:
            lines.append("### Superseded Decisions")
            for item in superseded_decs:
                d = item["key"]
                r = item["value"] or "Superseded by current session changes"
                lines.append(f"- 🚫 **[Superseded]** {d} — *Reason*: {r}")
            lines.append("")

    if steps:
        lines.extend([
            "---",
            "",
            "## 5. ⏩ Next Actionable Steps (Prioritized Roadmap)",
            "",
        ])
        for i, s in enumerate(steps, 1):
            prefix = f"P{i-1}" if i <= 3 else "P3"
            lines.append(f"- [ ] **{prefix}**: {s}")
        lines.append("")

    if blocker_list:
        lines.extend([
            "---",
            "",
            "## 6. ⚠️ Known Risks & Blockers",
            "",
        ])
        for b in blocker_list:
            lines.append(f"- ⚠️ {b}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 7. 🛡️ Control-Plane Reminder",
        "",
        "Handoff records are **data plane**. AGENTS.md and host runtime policies remain the **control plane**.",
        "Re-verify live facts and operational status before making production changes.",
        "",
    ])

    content = "\n".join(lines)

    # Determine file path
    safe_session = re.sub(r"[^\w.-]", "-", session_id) if session_id else "session"
    dest = handoff_dir / f"{day}_{safe_session}_handoff.md"
    if dest.exists():
        dest = handoff_dir / f"{day}_{safe_session}_handoff-{hid[-6:]}.md"

    closed_claims: list[str] = []
    if not dry_run:
        handoff_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

        # Handle claim closure
        if claim:
            closed_path = close_claim(root, claim, summary=clean_summary)
            closed_claims.append(str(closed_path.relative_to(root)).replace("\\", "/"))
        elif close_claim_file and session_id:
            # Auto-search active claims matching session_id
            claims_dirs = [
                root / "40_handoffs" / "session_claims",
                root / "40_跨Agent交接" / "会话认领",
            ]
            for cdir in claims_dirs:
                if cdir.is_dir():
                    for cfile in cdir.glob("*.md"):
                        if cfile.name == ".gitkeep":
                            continue
                        try:
                            fm_res = parse_frontmatter(cfile.read_text(encoding="utf-8"))
                            meta = fm_res.data
                            c_sess = str(meta.get("session_id") or "")
                            c_owner = str(meta.get("claimed_by") or "")
                            c_status = str(meta.get("status") or "")
                            if c_status == "active" and (c_sess == session_id or (c_owner and c_owner == owner)):
                                rel_c = str(cfile.relative_to(root)).replace("\\", "/")
                                closed_p = close_claim(root, rel_c, summary=clean_summary)
                                closed_claims.append(str(closed_p.relative_to(root)).replace("\\", "/"))
                        except Exception:
                            continue

    rel_dest = str(dest.relative_to(root)).replace("\\", "/")

    return {
        "ok": True,
        "action": "create_handoff",
        "dry_run": dry_run,
        "record_id": hid,
        "path": rel_dest,
        "absolute_path": str(dest),
        "project": slug,
        "session_id": session_id,
        "owner": owner,
        "tasks_completed_count": len(tasks),
        "evidence_count": len(evidence_list),
        "active_decisions_count": len(active_decs),
        "superseded_decisions_count": len(superseded_decs),
        "next_steps_count": len(steps),
        "blockers_count": len(blocker_list),
        "closed_claims": closed_claims,
        "summary": clean_summary,
    }
