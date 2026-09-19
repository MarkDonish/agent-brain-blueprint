"""Context builder: minimal sufficient pack for a project task.

Priority (high → low):
  Current Work > Active Decisions > Validation > Handoff > FTS hits > Summaries > Overview
Archive / superseded / expired are excluded by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_brain.layout import detect_layout
from agent_brain.retrieval.index import default_index_path, rebuild_index, status_index
from agent_brain.retrieval.query import search
from agent_brain.retrieval.scan import is_active_for_context


def estimate_tokens(text: str) -> int:
    # Rough chars/4 heuristic — enough for budget packing without a tokenizer dep.
    return max(1, (len(text) + 3) // 4)


def _read(vault: Path, rel: str, *, max_chars: int = 12000) -> str | None:
    path = vault / rel
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n\n…[truncated]\n"
    return text


def _list_project_md(vault: Path, layout, project: str, slot: str) -> list[Path]:
    root = layout.project_path(vault, project, slot)
    if not root.is_dir():
        return []
    files = [p for p in root.glob("*.md") if p.name != "README.md"]
    substantive = [p for p in files if p.name != "INDEX.md" and "索引" not in p.stem]
    selected = substantive or files
    return sorted(selected, key=lambda p: p.stat().st_mtime, reverse=True)


def _project_index(vault: Path, layout, project: str, slot: str) -> Path | None:
    root = layout.project_path(vault, project, slot)
    if not root.is_dir():
        return None
    files = [p for p in root.glob("*.md") if p.name != "README.md"]
    if not files:
        return None
    preferred = [p for p in files if p.name == "INDEX.md" or "索引" in p.stem]
    return sorted(preferred or files, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _section(title: str, body: str, source: str, *, profile: str = "verify") -> dict[str, Any]:
    if profile == "scout":
        # Compact/scout context is metadata-first.  Keep a short heading and
        # preview so the caller can decide which Markdown source to reopen.
        body = body[:600]
    return {
        "title": title,
        "source_path": source,
        "text": body,
        "tokens": estimate_tokens(body),
    }


def build_context(
    vault: Path,
    *,
    project: str,
    task: str = "",
    max_tokens: int = 16000,
    rebuild_if_missing: bool = True,
    fts_limit: int = 5,
    profile: str = "verify",
) -> dict[str, Any]:
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"vault not found: {vault}")
    if not project or "/" in project or "\\" in project or ".." in project:
        raise ValueError(f"invalid project slug: {project!r}")
    aliases = {"compact": "scout", "default": "verify", "full": "auditor"}
    selected_profile = aliases.get(str(profile or "verify").strip().lower(), str(profile or "verify").strip().lower())
    if selected_profile not in {"scout", "verify", "auditor"}:
        raise ValueError("profile must be scout, verify, or auditor (compact/default/full aliases)")
    layout = detect_layout(vault)

    index = default_index_path(vault)
    if rebuild_if_missing and not index.is_file():
        rebuild_index(vault)
        index = default_index_path(vault)

    try:
        retrieval_status = status_index(vault)
    except Exception as exc:  # read-only metadata is best effort for context
        retrieval_status = {"current_valid": False, "coverage_complete": False, "error": str(exc)}

    sections: list[dict[str, Any]] = []
    used = 0
    budget = max(500, int(max_tokens))
    truncated = False

    def try_add(sec: dict[str, Any] | None) -> bool:
        nonlocal used, truncated
        if not sec:
            return False
        # leave headroom
        if used + sec["tokens"] > budget and sections:
            truncated = True
            return False
        if used + sec["tokens"] > budget and not sections:
            # always allow first truncated section
            text = str(sec["text"])
            # shrink roughly
            allowed_chars = max(400, (budget - used) * 4)
            sec = dict(sec)
            sec["text"] = text[:allowed_chars] + "\n\n…[truncated for budget]\n"
            sec["tokens"] = estimate_tokens(sec["text"])
            sec["truncated"] = True
            truncated = True
        sections.append(sec)
        used += int(sec["tokens"])
        return True

    # 1) Overview
    overview_rel = layout.project_relative_path(project, "overview")
    text = _read(vault, overview_rel)
    if text:
        try_add(_section("PROJECT OVERVIEW", text, overview_rel, profile=selected_profile))

    # 2) Current work
    work_paths = _list_project_md(vault, layout, project, "current_work")
    if work_paths:
        work_path = work_paths[0]
        work_rel = str(work_path.relative_to(vault)).replace("\\", "/")
        text = _read(vault, work_rel)
        if text:
            try_add(_section("CURRENT WORK", text, work_rel, profile=selected_profile))

    # 3) Active decisions (newest first, up to 3)
    for path in _list_project_md(vault, layout, project, "decisions")[:3]:
        rel = str(path.relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if not text:
            continue
        # soft skip if superseded markers in frontmatter lines
        head = text[:400].lower()
        if "state: superseded" in head or "freshness: expired" in head:
            continue
        try_add(_section(f"DECISION · {path.stem}", text, rel, profile=selected_profile))

    # 4) Latest validation
    vals = _list_project_md(vault, layout, project, "validation")
    if vals:
        rel = str(vals[0].relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if text:
            try_add(_section(f"VALIDATION · {vals[0].stem}", text, rel, profile=selected_profile))

    # 5) Latest handoff
    hands = _list_project_md(vault, layout, project, "handoffs")
    if hands:
        rel = str(hands[0].relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if text:
            try_add(_section(f"HANDOFF · {hands[0].stem}", text, rel, profile=selected_profile))

    # 6) FTS candidates for task (if provided)
    if task.strip() and index.is_file():
        result = search(
            vault,
            task,
            project=project,
            include_inactive=False,
            limit=fts_limit,
        )
        if result.get("ok"):
            for hit in result.get("hits") or []:
                if not is_active_for_context(hit):
                    continue
                rel = str(hit.get("path") or "")
                # avoid duplicating already packed paths
                if any(s["source_path"] == rel for s in sections):
                    continue
                text = _read(vault, rel, max_chars=4000)
                if not text:
                    continue
                title = str(hit.get("title") or rel)
                try_add(_section(f"RETRIEVED CANDIDATE · {title}", text, rel, profile=selected_profile))

    # 7) Summaries index
    sum_path = _project_index(vault, layout, project, "summaries")
    sum_rel = (
        str(sum_path.relative_to(vault)).replace("\\", "/") if sum_path else ""
    )
    text = _read(vault, sum_rel) if sum_rel else None
    if text and used < budget * 0.95:
        try_add(_section("SUMMARIES INDEX", text, sum_rel, profile=selected_profile))

    packed = []
    truncated = truncated or any("…[truncated" in str(sec.get("text") or "") for sec in sections)
    for sec in sections:
        packed.append(
            f"## {sec['title']}\n\n"
            f"_source: `{sec['source_path']}` (canonical Markdown; reopen before high-risk acts)_\n\n"
            f"{sec['text'].rstrip()}\n"
        )

    header = (
        f"# Context pack\n\n"
        f"- project: `{project}`\n"
        f"- task: {task.strip() or '(none)'}\n"
        f"- max_tokens: {budget}\n"
        f"- profile: {selected_profile}\n"
        f"- estimated_tokens: {used}\n"
        f"- sections: {len(sections)}\n"
        f"- generation: `{retrieval_status.get('generation_id') or 'none'}`\n"
        f"- coverage_complete: `{bool(retrieval_status.get('coverage_complete'))}`\n"
        f"- truncated: `{truncated}`\n"
        f"- limitations: derived candidates only; reopen Markdown for truth\n"
        f"- rule: retrieval hits are **candidates**; Markdown is truth\n\n"
        f"---\n\n"
    )
    document = header + "\n---\n\n".join(packed)

    return {
        "project": project,
        "task": task,
        "max_tokens": budget,
        "estimated_tokens": used,
        "section_count": len(sections),
        "profile": selected_profile,
        "generation_id": retrieval_status.get("generation_id"),
        "coverage": {
            key: retrieval_status.get(key)
            for key in (
                "source_count",
                "indexed_count",
                "missing_source_count",
                "stale_source_count",
                "blocked_source_count",
                "coverage_complete",
            )
            if key in retrieval_status
        },
        "truncated": truncated,
        "limitations": ["Derived candidates are not authority; reopen canonical Markdown before acting."],
        "sections": [
            {"title": s["title"], "source_path": s["source_path"], "tokens": s["tokens"]}
            for s in sections
        ],
        "document": document,
        "derived_retrieval_used": bool(task.strip()),
        "canonical": "markdown",
    }
