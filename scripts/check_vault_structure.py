#!/usr/bin/env python3
"""Read-only check that a vault has the expected top-level skeleton."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_PATHS = (
    "00_entrypoint/SESSION_START_CARD.md",
    "10_projects",
    "20_agent_catalog",
    "30_global_decisions",
    "40_handoffs/session_claims",
    "50_retrieval",
    "60_templates",
    "70_inbox",
    "80_sensitive_isolation",
    "90_archive",
    "AGENTS.md",
)


def check_structure(root: Path) -> dict[str, object]:
    root = root.resolve()
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    projects = []
    projects_root = root / "10_projects"
    if projects_root.is_dir():
        for project in sorted(path for path in projects_root.iterdir() if path.is_dir()):
            expected = (
                "PROJECT_OVERVIEW.md",
                "10_current_work",
                "20_handoffs",
                "30_docs",
                "40_validation",
                "50_decisions",
                "60_summaries",
                "90_raw_sources",
            )
            project_missing = [name for name in expected if not (project / name).exists()]
            projects.append(
                {
                    "name": project.name,
                    "missing": project_missing,
                }
            )
    failures = [{"path": path, "errors": ["missing required path"]} for path in missing]
    for project in projects:
        if project["missing"]:
            failures.append(
                {
                    "path": f"10_projects/{project['name']}",
                    "errors": [f"missing: {item}" for item in project["missing"]],
                }
            )
    return {
        "read_only": True,
        "checked_path_count": len(REQUIRED_PATHS) + sum(8 for _ in projects),
        "project_count": len(projects),
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    report = check_structure(root)
    print(json.dumps(report, indent=2))
    return 0 if report["failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
