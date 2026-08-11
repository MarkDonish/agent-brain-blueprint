#!/usr/bin/env python3
"""Create a new Agent Brain vault from the public template."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.path_safety import PathSafetyError, validate_project_slug

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "templates" / "vault"
RECORD_TEMPLATES = REPO_ROOT / "templates"

PROJECT_FILES = {
    "PROJECT_OVERVIEW.md": "# {project}\n\n## Purpose\n\nReplace this fictional overview with source-backed project context.\n\n## 30-second entrypoint\n\n1. Read `10_current_work/INDEX.md`\n2. Read newest handoff and validation records\n3. Revalidate live facts before acting\n",
    "10_current_work/INDEX.md": "# Current Work\n\nNo active task.\n",
    "20_handoffs/INDEX.md": "# Handoffs\n\nStore project handoffs here.\n",
    "30_docs/INDEX.md": "# Docs\n\nStore non-sensitive design notes here.\n",
    "40_validation/INDEX.md": "# Validation\n\nStore evidence before closeout here.\n",
    "50_decisions/INDEX.md": "# Decisions\n\nUse the memory record template for durable decisions.\n",
    "60_summaries/INDEX.md": "# Summaries\n\nKeep session summaries short and source-backed.\n",
    "90_raw_sources/INDEX.md": "# Raw Sources\n\nStore source pointers only.\n",
}


def _copy_record_templates(destination: Path) -> list[str]:
    target = destination / "60_templates"
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(RECORD_TEMPLATES.glob("*.md")):
        shutil.copy2(path, target / path.name)
        copied.append(path.name)
    readme = target / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Local Templates\n\n"
            "These files are local copies of the public record templates.\n"
            "Keep the public blueprint repository under version control separately.\n",
            encoding="utf-8",
        )
    return copied


def _ensure_project(destination: Path, project: str) -> None:
    slug = validate_project_slug(project)
    root = destination / "10_projects" / slug
    for rel, content in PROJECT_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content.format(project=slug), encoding="utf-8")


def _refresh_session_card(destination: Path, project: str) -> None:
    slug = validate_project_slug(project)
    card = destination / "00_entrypoint" / "SESSION_START_CARD.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(
        f"""# Session Start Card

This vault was bootstrapped for local multi-agent memory.

1. Read this card and `10_projects/{slug}/PROJECT_OVERVIEW.md`.
2. Read current work, handoff, validation, decisions, and source indexes.
3. Create a session claim before editing shared records in multi-agent work.
4. Before contested writes, run claim gate with your session id so your own claim is excluded:
   `python3 scripts/check_claim_gate.py <vault> --session-id <id> --path <relative-path>`
   or `python3 scripts/check_claim_gate.py <vault> --claim 40_handoffs/session_claims/<claim>.md`
5. Never store secrets, raw conversations, databases, logs, or customer data here.
""",
        encoding="utf-8",
    )


def bootstrap(destination: Path, project: str = "example-app") -> dict[str, object]:
    slug = validate_project_slug(project)
    destination = destination.expanduser().resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise FileExistsError(f"destination exists and is not empty: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(TEMPLATE_ROOT, destination, dirs_exist_ok=destination.exists())
    shutil.copy2(REPO_ROOT / "AGENTS.md", destination / "AGENTS.md")
    copied_templates = _copy_record_templates(destination)
    _ensure_project(destination, slug)
    _refresh_session_card(destination, slug)

    gitignore = destination / ".gitignore"
    if not gitignore.exists():
        shutil.copy2(TEMPLATE_ROOT / ".gitignore", gitignore)

    return {
        "destination": str(destination),
        "project": slug,
        "copied_record_templates": copied_templates,
        "read_only": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--project", default="example-app", help="project folder name under 10_projects/")
    args = parser.parse_args()
    try:
        result = bootstrap(args.destination, project=args.project)
    except FileExistsError as exc:
        parser.error(str(exc))
    except PathSafetyError as exc:
        parser.error(str(exc))
    print(f"created vault: {result['destination']}")
    print(f"project: {result['project']}")
    print(f"copied templates: {', '.join(result['copied_record_templates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
