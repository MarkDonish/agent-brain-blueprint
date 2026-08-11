#!/usr/bin/env python3
"""Run the blueprint's read-only structural checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(script: str, vault: str) -> int:
    completed = subprocess.run([sys.executable, str(ROOT / "scripts" / script), vault], check=False)
    return completed.returncode


def main() -> int:
    vault = sys.argv[1] if len(sys.argv) > 1 else "templates/vault"
    results = [run("check_memory_governance.py", vault), run("check_session_claims.py", vault)]
    return 0 if all(code == 0 for code in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
