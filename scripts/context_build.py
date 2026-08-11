#!/usr/bin/env python3
"""Compatibility wrapper: context pack builder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_brain.context.builder import build_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--max-tokens", type=int, default=16000)
    args = parser.parse_args()
    pack = build_context(
        args.vault,
        project=args.project,
        task=args.task,
        max_tokens=args.max_tokens,
    )
    print(pack["document"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
