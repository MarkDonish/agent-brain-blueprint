#!/usr/bin/env python3
"""Run the blueprint's read-only structural and governance checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "check_vault_structure.py",
    "check_memory_governance.py",
    "check_session_claims.py",
)


def run_check(script: str, vault: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(vault)],
        check=False,
        capture_output=True,
        text=True,
    )
    payload: dict[str, object]
    stdout = completed.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {"raw_stdout": stdout}
    return {
        "script": script,
        "exit_code": completed.returncode,
        "report": payload,
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", nargs="?", type=Path, default=Path("templates/vault"))
    parser.add_argument("--json", action="store_true", help="print a combined JSON report")
    args = parser.parse_args()
    vault = args.vault

    results = [run_check(script, vault) for script in CHECKS]
    failure_count = sum(1 for item in results if item["exit_code"] != 0)
    summary = {
        "read_only": True,
        "vault": str(vault),
        "check_count": len(results),
        "failure_count": failure_count,
        "checks": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"doctor vault: {vault}")
        for item in results:
            status = "PASS" if item["exit_code"] == 0 else "FAIL"
            report = item["report"] if isinstance(item["report"], dict) else {}
            detail = ""
            if "failure_count" in report:
                detail = f" failures={report['failure_count']}"
            elif "checked_file_count" in report:
                detail = f" checked={report['checked_file_count']}"
            print(f"  [{status}] {item['script']}{detail}")
            if item["stderr"]:
                print(f"    stderr: {item['stderr'][:300]}")
        print(f"summary: {failure_count} failed / {len(results)} checks")

    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
