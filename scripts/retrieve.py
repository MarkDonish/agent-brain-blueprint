#!/usr/bin/env python3
"""Compatibility wrapper: FTS search (candidates only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_brain.retrieval.query import search  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path)
    parser.add_argument("query")
    parser.add_argument("--project", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    result = search(args.vault, args.query, project=args.project, limit=args.limit)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
