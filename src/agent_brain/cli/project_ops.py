"""Project list / add helpers (vault data plane only)."""

from __future__ import annotations

from pathlib import Path

from agent_brain.paths import ensure_scripts_on_path


PROJECT_FILES = {
    "PROJECT_OVERVIEW.md": (
        "# {project}\n\n## Purpose\n\nReplace this overview with source-backed project context.\n\n"
        "## 30-second entrypoint\n\n"
        "1. Read `10_current_work/INDEX.md`\n"
        "2. Read newest handoff and validation records\n"
        "3. Revalidate live facts before acting\n"
    ),
    "10_current_work/INDEX.md": "# Current Work\n\nNo active task.\n",
    "20_handoffs/INDEX.md": "# Handoffs\n\nStore project handoffs here.\n",
    "30_docs/INDEX.md": "# Docs\n\nStore non-sensitive design notes here.\n",
    "40_validation/INDEX.md": "# Validation\n\nStore evidence before closeout here.\n",
    "50_decisions/INDEX.md": "# Decisions\n\nUse the memory record template for durable decisions.\n",
    "60_summaries/INDEX.md": "# Summaries\n\nKeep session summaries short and source-backed.\n",
    "90_raw_sources/INDEX.md": "# Raw Sources\n\nStore source pointers only.\n",
}


def list_projects(vault: Path) -> list[str]:
    root = vault.expanduser().resolve() / "10_projects"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def add_project(vault: Path, project: str) -> Path:
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, project_dir, validate_project_slug

    slug = validate_project_slug(project)
    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")
    try:
        dest = project_dir(root, slug)
    except PathSafetyError:
        raise
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"project already exists and is not empty: {dest}")
    for rel, content in PROJECT_FILES.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content.format(project=slug), encoding="utf-8")
    return dest
