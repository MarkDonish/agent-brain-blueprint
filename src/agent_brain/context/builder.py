"""Context builder: minimal sufficient pack for a project task.

Priority (high → low):
  Current Work > Active Decisions > Validation > Handoff > FTS hits > Summaries > Overview
Archive / superseded / expired are excluded by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_brain.retrieval.index import default_index_path, rebuild_index
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


def _list_project_md(vault: Path, project: str, sub: str) -> list[Path]:
    root = vault / "10_projects" / project / sub
    if not root.is_dir():
        return []
    return sorted(
        [p for p in root.glob("*.md") if p.name not in {"INDEX.md", "README.md"}],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _section(title: str, body: str, source: str) -> dict[str, Any]:
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
) -> dict[str, Any]:
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"vault not found: {vault}")
    if not project or "/" in project or "\\" in project or ".." in project:
        raise ValueError(f"invalid project slug: {project!r}")

    index = default_index_path(vault)
    if rebuild_if_missing and not index.is_file():
        rebuild_index(vault)

    sections: list[dict[str, Any]] = []
    used = 0
    budget = max(500, int(max_tokens))

    def try_add(sec: dict[str, Any] | None) -> bool:
        nonlocal used
        if not sec:
            return False
        # leave headroom
        if used + sec["tokens"] > budget and sections:
            return False
        if used + sec["tokens"] > budget and not sections:
            # always allow first truncated section
            text = str(sec["text"])
            # shrink roughly
            allowed_chars = max(400, (budget - used) * 4)
            sec = dict(sec)
            sec["text"] = text[:allowed_chars] + "\n\n…[truncated for budget]\n"
            sec["tokens"] = estimate_tokens(sec["text"])
        sections.append(sec)
        used += int(sec["tokens"])
        return True

    # 1) Overview
    overview_rel = f"10_projects/{project}/PROJECT_OVERVIEW.md"
    text = _read(vault, overview_rel)
    if text:
        try_add(_section("PROJECT OVERVIEW", text, overview_rel))

    # 2) Current work
    work_rel = f"10_projects/{project}/10_current_work/INDEX.md"
    text = _read(vault, work_rel)
    if text:
        try_add(_section("CURRENT WORK", text, work_rel))

    # 3) Active decisions (newest first, up to 3)
    for path in _list_project_md(vault, project, "50_decisions")[:3]:
        rel = str(path.relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if not text:
            continue
        # soft skip if superseded markers in frontmatter lines
        head = text[:400].lower()
        if "state: superseded" in head or "freshness: expired" in head:
            continue
        try_add(_section(f"DECISION · {path.stem}", text, rel))

    # 4) Latest validation
    vals = _list_project_md(vault, project, "40_validation")
    if vals:
        rel = str(vals[0].relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if text:
            try_add(_section(f"VALIDATION · {vals[0].stem}", text, rel))

    # 5) Latest handoff
    hands = _list_project_md(vault, project, "20_handoffs")
    if hands:
        rel = str(hands[0].relative_to(vault)).replace("\\", "/")
        text = _read(vault, rel)
        if text:
            try_add(_section(f"HANDOFF · {hands[0].stem}", text, rel))

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
                try_add(_section(f"RETRIEVED CANDIDATE · {title}", text, rel))

    # 7) Summaries index
    sum_rel = f"10_projects/{project}/60_summaries/INDEX.md"
    text = _read(vault, sum_rel)
    if text and used < budget * 0.95:
        try_add(_section("SUMMARIES INDEX", text, sum_rel))

    packed = []
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
        f"- estimated_tokens: {used}\n"
        f"- sections: {len(sections)}\n"
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
        "sections": [
            {"title": s["title"], "source_path": s["source_path"], "tokens": s["tokens"]}
            for s in sections
        ],
        "document": document,
        "derived_retrieval_used": bool(task.strip()),
        "canonical": "markdown",
    }
