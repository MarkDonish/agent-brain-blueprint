#!/usr/bin/env python3
"""Read-only pre-write claim gate.

Given a vault root and planned vault-relative paths, report conflicts with
currently active session claims. This is not a filesystem lock.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_session_claims import claim_result, collect_claim_paths, overlaps, safe_relative_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="vault-relative path that a session plans to write (repeatable)",
    )
    parser.add_argument("--claims-dir", type=Path, default=Path("40_handoffs/session_claims"))
    parser.add_argument("--fail-on-expired", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    claims_dir = args.claims_dir if args.claims_dir.is_absolute() else root / args.claims_dir
    planned: list[str] = []
    errors: list[str] = []
    for raw in args.paths:
        safe = safe_relative_path(root, raw)
        if safe is None:
            errors.append(f"unsafe planned path: {raw}")
        else:
            planned.append(safe)

    if not planned and not errors:
        errors.append("no --path provided")

    results = [
        claim_result(root, path, fail_on_expired=args.fail_on_expired)
        for path in collect_claim_paths(root, claims_dir)
    ]
    active = [item for item in results if item["active"] and not item["errors"]]
    conflicts = []
    for claim in active:
        for left in planned:
            for right in claim["paths"]:
                if overlaps(left, str(right)):
                    conflicts.append(
                        {
                            "planned_path": left,
                            "claim_path": claim["path"],
                            "claimed_path": right,
                            "session_id": claim.get("session_id"),
                            "claimed_by": claim.get("claimed_by"),
                        }
                    )

    payload = {
        "read_only": True,
        "trusted_local_filesystem_only": True,
        "is_lock": False,
        "planned_paths": planned,
        "active_claim_count": len(active),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "errors": errors,
        "allowed": not errors and not conflicts,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
