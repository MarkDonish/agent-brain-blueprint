#!/usr/bin/env python3
"""Compatibility wrapper: rebuild derived FTS index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_brain.retrieval.index import rebuild_index  # noqa: E402


def main() -> int:
    vault = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    report = rebuild_index(vault)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
