#!/usr/bin/env python3
"""Read-only privacy scan for the public blueprint checkout.

This is a pre-publish safety net. It is intentionally conservative and may
produce false positives that still deserve a human look.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "indexes",
    "cache",
    "logs",
    "data",
    "private",
}

TEXT_SUFFIXES = {
    "",
    ".md",
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
    ".json",
    ".sh",
    ".gitignore",
    ".gitkeep",
}

# Patterns that should never appear in a public blueprint.
SECRET_PATTERNS = (
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_sk", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic_bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
)

# Patterns that are usually local personal leakage.
RISK_PATTERNS = (
    ("home_path", re.compile(r"/Users/[A-Za-z0-9._-]+")),
    ("windows_user_path", re.compile(r"(?i)\bC:\\Users\\[A-Za-z0-9._-]+")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)

ALLOWLIST_SNIPPETS = {
    # Common documentation examples that are safe in this repository.
    "your-account",
    "demo-user",
    "example-app",
    "/path/to/",
    "127.0.0.1",
    "0.0.0.0",
    "localhost",
}

SECRET_PATTERN_NAMES = {name for name, _ in SECRET_PATTERNS} | {"unreadable_text"}


def iter_text_files(root: Path):
    root = root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        # Only skip directories inside the scanned tree. Do not use absolute
        # system prefixes such as macOS /private/tmp.
        if any(part in SKIP_DIR_NAMES for part in relative.parts[:-1]):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore", ".gitkeep"}:
            continue
        yield path


def scan_file(root: Path, path: Path) -> list[dict[str, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [
            {
                "path": str(path.relative_to(root)),
                "severity": "unreadable_text",
                "line": 0,
                "detail": "could not read as utf-8 text",
            }
        ]

    findings: list[dict[str, object]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if any(snippet in stripped for snippet in ALLOWLIST_SNIPPETS):
            # Still check hard secrets on allowlisted lines.
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {
                            "path": str(path.relative_to(root)),
                            "severity": name,
                            "line": line_no,
                            "detail": stripped[:160],
                        }
                    )
            continue
        for name, pattern in SECRET_PATTERNS + RISK_PATTERNS:
            if pattern.search(line):
                findings.append(
                    {
                        "path": str(path.relative_to(root)),
                        "severity": name,
                        "line": line_no,
                        "detail": stripped[:160],
                    }
                )
    return findings


def scan(root: Path) -> dict[str, object]:
    root = root.resolve()
    findings: list[dict[str, object]] = []
    checked = 0
    for path in iter_text_files(root):
        checked += 1
        findings.extend(scan_file(root, path))

    secret_hits = [item for item in findings if item["severity"] in SECRET_PATTERN_NAMES]
    risk_hits = [item for item in findings if item["severity"] not in SECRET_PATTERN_NAMES]
    return {
        "read_only": True,
        "checked_file_count": checked,
        "secret_finding_count": len(secret_hits),
        "risk_finding_count": len(risk_hits),
        "failure_count": len(secret_hits),
        "secret_findings": secret_hits,
        "risk_findings": risk_hits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail on risk findings such as home paths and emails",
    )
    args = parser.parse_args()
    report = scan(args.root)
    print(json.dumps(report, indent=2))
    if report["secret_finding_count"]:
        return 2
    if args.strict and report["risk_finding_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
