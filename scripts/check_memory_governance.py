#!/usr/bin/env python3
"""Read-only check for required frontmatter on durable memory records."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path


REQUIRED = ("memory_type", "source", "confidence", "freshness", "scope", "risk_boundary", "next_review", "owner")


def frontmatter(text: str) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    return match.group(1) if match else ""


def governed_files(root: Path) -> Iterator[Path]:
    for path in sorted((root / "30_global_decisions").glob("*.md")):
        if path.name not in {"README.md", "INDEX.md"}:
            yield path
    for path in sorted((root / "10_projects").glob("*/50_decisions/*.md")):
        if path.name not in {"README.md", "INDEX.md"}:
            yield path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures = []
    files = list(governed_files(root))
    for path in files:
        block = frontmatter(path.read_text(encoding="utf-8"))
        missing = [field for field in REQUIRED if not re.search(rf"(?m)^{re.escape(field)}\s*:", block)]
        if missing:
            failures.append({"path": str(path.relative_to(root)), "missing": missing})
    print(json.dumps({"read_only": True, "checked_file_count": len(files), "failure_count": len(failures), "failures": failures}, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
