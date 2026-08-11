#!/usr/bin/env python3
"""Write or refresh .agent-brain/manifest.json (migration helper for pre-0.5 vaults)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.vault_format import TOOL_VERSION, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--created-with",
        default=TOOL_VERSION,
        help="value for created_with (default: current tool version)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing manifest",
    )
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    path = root / ".agent-brain" / "manifest.json"
    if path.exists() and not args.force:
        print(f"manifest already exists: {path} (use --force to overwrite)")
        return 0
    written = write_manifest(root, created_with=args.created_with)
    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
