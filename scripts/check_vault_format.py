#!/usr/bin/env python3
"""Read-only vault format / version compatibility check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.vault_format import (
    SUPPORTED_VAULT_FORMAT_VERSIONS,
    TOOL_VERSION,
    VAULT_FORMAT_VERSION,
    read_manifest,
    validate_manifest,
)


def check_format(root: Path, *, require_manifest: bool = False) -> dict[str, object]:
    root = root.resolve()
    data = read_manifest(root)
    errors = validate_manifest(data)
    warnings: list[str] = []
    if data is None and not require_manifest:
        # Pre-0.5 vaults: warn only so old trees stay usable.
        warnings = list(errors)
        errors = []
    return {
        "read_only": True,
        "tool_version": TOOL_VERSION,
        "expected_vault_format_version": VAULT_FORMAT_VERSION,
        "supported_vault_format_versions": sorted(SUPPORTED_VAULT_FORMAT_VERSIONS),
        "manifest_present": data is not None,
        "manifest": data,
        "warning_count": len(warnings),
        "warnings": warnings,
        "failure_count": len(errors),
        "failures": [{"path": ".agent-brain/manifest.json", "errors": errors}] if errors else [],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="fail when manifest is missing (default: warn only for pre-0.5 vaults)",
    )
    args = parser.parse_args()
    report = check_format(args.root, require_manifest=args.require_manifest)
    print(json.dumps(report, indent=2))
    return 0 if report["failure_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
