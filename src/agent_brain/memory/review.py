"""List records that need review (past review_after / next_review or state)."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from agent_brain.paths import ensure_scripts_on_path

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    match = _DATE_RE.match(str(value).strip())
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def list_review_due(
    vault: Path,
    *,
    project: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    ensure_scripts_on_path()
    from lib.frontmatter import parse_frontmatter
    from lib.path_safety import validate_project_slug

    root = vault.expanduser().resolve()
    today = today or datetime.now(timezone.utc).date()
    project_slug = validate_project_slug(project) if project else None

    due: list[dict[str, Any]] = []
    checked = 0
    for path in sorted(root.rglob("*.md")):
        if not path.is_file() or path.name in {"README.md", "INDEX.md"}:
            continue
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
        if any(p in {".git", "indexes", "80_sensitive_isolation", "60_templates"} for p in path.relative_to(root).parts):
            continue
        if project_slug:
            prefix = f"10_projects/{project_slug}/"
            if not (rel.startswith(prefix) or rel.startswith("30_global_decisions/")):
                continue
        # focus durable locations
        if not (
            "/50_decisions/" in rel
            or rel.startswith("30_global_decisions/")
            or "/40_validation/" in rel
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if not text.startswith("---"):
            continue
        checked += 1
        parsed = parse_frontmatter(text)
        data = parsed.data
        state = str(data.get("state") or "")
        reasons: list[str] = []
        if state == "review-required":
            reasons.append("state=review-required")
        for field in ("review_after", "next_review"):
            d = _parse_date(data.get(field))
            if d is not None and d < today:
                reasons.append(f"{field} past ({d.isoformat()})")
        if reasons:
            due.append(
                {
                    "path": rel,
                    "record_id": data.get("record_id"),
                    "title": data.get("title") or path.stem,
                    "state": state or None,
                    "reasons": reasons,
                }
            )

    return {
        "read_only": True,
        "checked_record_count": checked,
        "due_count": len(due),
        "as_of": today.isoformat(),
        "project": project_slug,
        "due": due,
    }
