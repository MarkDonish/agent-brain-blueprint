#!/usr/bin/env python3
"""Read-only privacy scan for the public blueprint checkout.

This is a pre-publish safety net. It is intentionally conservative and may
produce false positives that still deserve a human look.

Hard-secret findings never include the raw secret in report detail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
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
    ("github_fine_grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("openai_sk", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic_bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("jwt_like", re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")),
)

# Patterns that are usually local personal leakage.
RISK_PATTERNS = (
    ("home_path", re.compile(r"/Users/[A-Za-z0-9._-]+")),
    ("windows_user_path", re.compile(r"(?i)\bC:\\Users\\[A-Za-z0-9._-]+")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)

# Allowlist snippets live in `.privacy-allowlist` (single source of truth);
# load_allowlist() reads them. Nothing is duplicated here.

SECRET_PATTERN_NAMES = {name for name, _ in SECRET_PATTERNS} | {"unreadable_text"}


def load_allowlist(root: Path) -> set[str]:
    path = root / ".privacy-allowlist"
    if not path.exists():
        return set()
    items: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        items.add(text)
    return items


def fingerprint_secret(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]}"


def redact_secret_detail(line: str, pattern: re.Pattern[str], match: re.Match[str]) -> str:
    """Return a short detail string with the matched secret replaced by [REDACTED]."""
    start, end = match.span()
    redacted = f"{line[:start]}[REDACTED]{line[end:]}"
    stripped = redacted.strip()
    if len(stripped) > 160:
        stripped = stripped[:157] + "..."
    return stripped


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


def _finding(
    relative: str,
    name: str,
    line_no: int,
    *,
    detail: str,
    fingerprint: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "path": relative,
        "severity": name,
        "line": line_no,
        "detail": detail,
    }
    if fingerprint:
        item["fingerprint"] = fingerprint
    return item


def scan_file(root: Path, path: Path, allowlist: set[str]) -> list[dict[str, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [
            _finding(
                str(path.relative_to(root)),
                "unreadable_text",
                0,
                detail="could not read as utf-8 text",
            )
        ]

    findings: list[dict[str, object]] = []
    relative = str(path.relative_to(root))

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Hard secrets are always reported, even inside allowlisted text.
        for name, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(
                    _finding(
                        relative,
                        name,
                        line_no,
                        detail=redact_secret_detail(line, pattern, match),
                        fingerprint=fingerprint_secret(match.group(0)),
                    )
                )
        for name, pattern in RISK_PATTERNS:
            for match in pattern.finditer(line):
                matched = match.group(0)
                # Match-level allowlisting: suppress only this specific match
                # when the matched text itself contains an allowlisted snippet.
                # A real leak elsewhere on the same line is still reported.
                if any(item in matched for item in allowlist):
                    continue
                detail = f"{matched} <- {stripped[:140]}" if len(stripped) > len(matched) else matched
                findings.append(_finding(relative, name, line_no, detail=detail))
    return findings


def scan(root: Path) -> dict[str, object]:
    root = root.resolve()
    allowlist = load_allowlist(root)
    findings: list[dict[str, object]] = []
    checked = 0
    for path in iter_text_files(root):
        checked += 1
        findings.extend(scan_file(root, path, allowlist))

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
