#!/usr/bin/env python3
"""Create a new Agent Brain vault from the public template."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "templates" / "vault"
RECORD_TEMPLATES = REPO_ROOT / "templates"


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


def bootstrap(destination: Path) -> dict[str, object]:
    destination = destination.expanduser().resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise FileExistsError(f"destination exists and is not empty: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(TEMPLATE_ROOT, destination, dirs_exist_ok=destination.exists())
    shutil.copy2(REPO_ROOT / "AGENTS.md", destination / "AGENTS.md")
    copied_templates = _copy_record_templates(destination)

    gitignore = destination / ".gitignore"
    if not gitignore.exists():
        shutil.copy2(TEMPLATE_ROOT / ".gitignore", gitignore)

    return {
        "destination": str(destination),
        "copied_record_templates": copied_templates,
        "read_only": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = bootstrap(args.destination)
    except FileExistsError as exc:
        parser.error(str(exc))
    print(f"created vault: {result['destination']}")
    print(f"copied templates: {', '.join(result['copied_record_templates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
