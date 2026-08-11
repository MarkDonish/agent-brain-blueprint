#!/usr/bin/env python3
"""Create a new Agent Brain vault from the public template."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "templates" / "vault"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    destination = args.destination.expanduser()
    if destination.exists() and any(destination.iterdir()):
        parser.error("destination exists and is not empty")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_ROOT, destination, dirs_exist_ok=True)
    shutil.copy2(REPO_ROOT / "AGENTS.md", destination / "AGENTS.md")
    print(f"created vault: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
