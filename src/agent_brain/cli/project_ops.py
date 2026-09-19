"""Project list / add helpers (vault data plane only)."""

from __future__ import annotations

from pathlib import Path

from agent_brain.layout import detect_layout
from agent_brain.paths import ensure_scripts_on_path


def _project_files(layout, project: str) -> dict[str, str]:
    """Build a project skeleton using the selected layout vocabulary."""

    def index_name(slot: str) -> str:
        return str(layout.index_files.get(slot) or "INDEX.md")

    overview = (
        f"# {project}\n\n## Purpose\n\nReplace this overview with source-backed project context.\n\n"
        f"## 30-second entrypoint\n\n"
        f"1. Read `{layout.relative_path('current_work')}/{index_name('current_work')}`\n"
        f"2. Read newest handoff and validation records\n"
        f"3. Revalidate live facts before acting\n"
    )
    return {
        layout.relative_path("overview"): overview,
        f"{layout.relative_path('current_work')}/{index_name('current_work')}": "# Current Work\n\nNo active task.\n",
        f"{layout.relative_path('handoffs')}/{index_name('handoffs')}": "# Handoffs\n\nStore project handoffs here.\n",
        f"{layout.relative_path('docs')}/{index_name('docs')}": "# Docs\n\nStore non-sensitive design notes here.\n",
        f"{layout.relative_path('validation')}/{index_name('validation')}": "# Validation\n\nStore evidence before closeout here.\n",
        f"{layout.relative_path('decisions')}/{index_name('decisions')}": "# Decisions\n\nUse the memory record template for durable decisions.\n",
        f"{layout.relative_path('summaries')}/{index_name('summaries')}": "# Summaries\n\nKeep session summaries short and source-backed.\n",
        f"{layout.relative_path('raw_sources')}/{index_name('raw_sources')}": "# Raw Sources\n\nStore source pointers only.\n",
    }


def list_projects(vault: Path) -> list[str]:
    root = vault.expanduser().resolve()
    if not root.is_dir():
        return []
    layout = detect_layout(root)
    projects_root = layout.path(root, "projects_root")
    if not projects_root.is_dir():
        return []
    return sorted(p.name for p in projects_root.iterdir() if p.is_dir())


def add_project(vault: Path, project: str) -> Path:
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, validate_project_slug

    slug = validate_project_slug(project)
    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")
    layout = detect_layout(root)
    try:
        dest = layout.project_dir(root, slug)
    except PathSafetyError:
        raise
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"project already exists and is not empty: {dest}")
    for rel, content in _project_files(layout, slug).items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content.format(project=slug), encoding="utf-8")
    return dest
