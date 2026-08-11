#!/usr/bin/env python3
"""Create missing vault skeleton paths. Default is dry-run."""

from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_PATHS = (
    "00_entrypoint/SESSION_START_CARD.md",
    "10_projects",
    "20_agent_catalog/README.md",
    "30_global_decisions/README.md",
    "40_handoffs/session_claims/.gitkeep",
    "50_retrieval/README.md",
    "60_templates/README.md",
    "70_inbox/README.md",
    "80_sensitive_isolation/README.md",
    "90_archive/README.md",
    "AGENTS.md",
)

PROJECT_PATHS = (
    "PROJECT_OVERVIEW.md",
    "10_current_work/INDEX.md",
    "20_handoffs/INDEX.md",
    "30_docs/INDEX.md",
    "40_validation/INDEX.md",
    "50_decisions/INDEX.md",
    "60_summaries/INDEX.md",
    "90_raw_sources/INDEX.md",
)


def missing_paths(root: Path, project: str | None = None) -> list[Path]:
    missing: list[Path] = []
    for rel in REQUIRED_PATHS:
        path = root / rel
        if not path.exists():
            missing.append(path)
    if project:
        for rel in PROJECT_PATHS:
            path = root / "10_projects" / project / rel
            if not path.exists():
                missing.append(path)
    return missing


def apply(paths: list[Path]) -> None:
    for path in paths:
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                if path.name == ".gitkeep":
                    path.write_text("", encoding="utf-8")
                elif path.suffix == ".md":
                    title = path.stem.replace("_", " ")
                    path.write_text(f"# {title}\n\nPlaceholder created by fix_vault_structure.py.\n", encoding="utf-8")
                else:
                    path.write_text("", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--project", default=None)
    parser.add_argument("--apply", action="store_true", help="create missing paths (otherwise dry-run)")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    missing = missing_paths(root, args.project)
    print(f"vault: {root}")
    print(f"missing: {len(missing)}")
    for path in missing:
        print(f"  - {path.relative_to(root)}")
    if args.apply:
        apply(missing)
        print("applied")
    else:
        print("dry-run only; re-run with --apply to create placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
