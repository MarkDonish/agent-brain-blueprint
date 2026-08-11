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

REPAIR_HINTS = {
    "check_vault_structure.py": "Create missing skeleton dirs/files or run scripts/fix_vault_structure.py --apply",
    "check_memory_governance.py": "Add required frontmatter fields from schemas/ and templates/memory_record.md",
    "check_session_claims.py": "Fix claim fields, close conflicting claims, or set expires_at / closeout_state",
}


def run_check(script: str, vault: Path, extra_args: list[str] | None = None) -> dict[str, object]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), str(vault)]
    if extra_args:
        cmd.extend(extra_args)
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
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
        "hint": REPAIR_HINTS.get(script, ""),
    }


def summarize_failures(report: dict[str, object]) -> list[str]:
    lines: list[str] = []
    failures = report.get("failures")
    if isinstance(failures, list):
        for item in failures[:5]:
            if not isinstance(item, dict):
                continue
            path = item.get("path", "?")
            errors = item.get("errors") or item.get("missing") or []
            if isinstance(errors, list) and errors:
                lines.append(f"{path}: {errors[0]}")
            else:
                lines.append(str(path))
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", nargs="?", type=Path, default=Path("templates/vault"))
    parser.add_argument("--json", action="store_true", help="print a combined JSON report")
    parser.add_argument("--strict", action="store_true", help="promote soft warnings to failures where supported")
    parser.add_argument("--project", default=None, help="limit structure/governance messaging to one project name")
    args = parser.parse_args()
    vault = args.vault

    extra = {
        "check_memory_governance.py": ["--strict-soft"] if args.strict else [],
        "check_session_claims.py": ["--fail-on-expired"] if args.strict else [],
    }
    results = [run_check(script, vault, extra.get(script)) for script in CHECKS]

    # Optional project filter is advisory for human output; checkers still run whole vault.
    if args.project:
        project_prefix = f"10_projects/{args.project}/"
        for item in results:
            report = item["report"]
            if not isinstance(report, dict):
                continue
            for key in ("failures", "warnings"):
                values = report.get(key)
                if isinstance(values, list):
                    report[key] = [
                        row
                        for row in values
                        if isinstance(row, dict) and project_prefix in str(row.get("path", ""))
                    ]

    failure_count = sum(1 for item in results if item["exit_code"] != 0)
    warning_count = 0
    for item in results:
        report = item["report"] if isinstance(item["report"], dict) else {}
        warning_count += int(report.get("warning_count") or 0)

    summary = {
        "read_only": True,
        "vault": str(vault),
        "check_count": len(results),
        "failure_count": failure_count,
        "warning_count": warning_count,
        "checks": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"doctor vault: {vault}")
        for item in results:
            status = "PASS" if item["exit_code"] == 0 else "FAIL"
            report = item["report"] if isinstance(item["report"], dict) else {}
            detail_parts = []
            if "failure_count" in report:
                detail_parts.append(f"failures={report['failure_count']}")
            if "warning_count" in report:
                detail_parts.append(f"warnings={report['warning_count']}")
            if "checked_file_count" in report:
                detail_parts.append(f"checked={report['checked_file_count']}")
            detail = (" " + " ".join(detail_parts)) if detail_parts else ""
            print(f"  [{status}] {item['script']}{detail}")
            for line in summarize_failures(report):
                print(f"    - {line}")
            if item["exit_code"] != 0 and item["hint"]:
                print(f"    fix: {item['hint']}")
            if item["stderr"]:
                print(f"    stderr: {item['stderr'][:300]}")
        print(f"summary: {failure_count} failed / {len(results)} checks; warnings={warning_count}")

    if args.strict and warning_count and failure_count == 0:
        return 2
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
