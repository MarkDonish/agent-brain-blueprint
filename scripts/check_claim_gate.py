#!/usr/bin/env python3
"""Read-only pre-write claim gate.

Given a vault root and planned vault-relative paths, report conflicts with
currently active session claims. This is not a filesystem lock.

Self-conflict: pass --session-id (or --claim) so the caller's own claim is
excluded from conflict detection.

Fail-closed: malformed or unreadable existing claims deny the gate unless
--ignore-invalid-claims is set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_session_claims import claim_result, collect_claim_paths, overlaps
from lib.path_safety import safe_relative_path, safe_vault_join


def _run_gate(
    root: Path,
    planned: list[str],
    *,
    claims_dir: Path,
    session_id: str | None = None,
    fail_on_expired: bool = False,
    ignore_invalid_claims: bool = False,
) -> dict[str, object]:
    results = [
        claim_result(root, path, fail_on_expired=fail_on_expired)
        for path in collect_claim_paths(root, claims_dir)
    ]

    invalid = [item for item in results if item["errors"]]
    invalid_findings = [
        {
            "claim_path": item["path"],
            "errors": item["errors"],
            "reason": "invalid_existing_claim",
        }
        for item in invalid
    ]

    # Active claims with format errors still occupy their planned paths, so
    # they participate in conflict detection (and are reported as invalid).
    active = [item for item in results if item["active"]]
    if session_id:
        active_for_conflict = [
            item for item in active if str(item.get("session_id") or "") != session_id
        ]
    else:
        active_for_conflict = active

    conflicts = []
    for claim in active_for_conflict:
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

    errors: list[str] = []
    if invalid_findings and not ignore_invalid_claims:
        errors.append("invalid_existing_claim")

    allowed = not conflicts and not errors

    return {
        "read_only": True,
        "trusted_local_filesystem_only": True,
        "is_lock": False,
        "planned_paths": planned,
        "session_id": session_id,
        "active_claim_count": len(active),
        "considered_claim_count": len(active_for_conflict),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "invalid_claim_count": len(invalid_findings),
        "invalid_claims": invalid_findings,
        "errors": errors,
        "allowed": allowed,
        "ignore_invalid_claims": ignore_invalid_claims,
    }


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
    parser.add_argument(
        "--session-id",
        default=None,
        help="exclude active claims with this session_id (caller self)",
    )
    parser.add_argument(
        "--claim",
        type=Path,
        default=None,
        help="caller claim file (vault-relative or absolute under vault); sets session-id and planned paths if --path omitted",
    )
    parser.add_argument("--claims-dir", type=Path, default=Path("40_handoffs/session_claims"))
    parser.add_argument("--fail-on-expired", action="store_true")
    parser.add_argument(
        "--ignore-invalid-claims",
        action="store_true",
        help="do not fail closed when other claims are malformed/unreadable (unsafe)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    claims_dir = args.claims_dir if args.claims_dir.is_absolute() else root / args.claims_dir
    errors: list[str] = []
    planned: list[str] = []
    session_id = args.session_id

    if args.claim is not None:
        raw_claim = str(args.claim)
        if Path(raw_claim).is_absolute():
            try:
                claim_path = Path(raw_claim).resolve(strict=False)
                claim_path.relative_to(root)
            except (OSError, RuntimeError, ValueError):
                errors.append(f"claim path outside vault: {raw_claim}")
                claim_path = None
        else:
            rel = safe_relative_path(root, raw_claim)
            if rel is None:
                errors.append(f"unsafe claim path: {raw_claim}")
                claim_path = None
            else:
                claim_path = safe_vault_join(root, *rel.split("/"))
        if claim_path is not None:
            caller = claim_result(root, claim_path, fail_on_expired=args.fail_on_expired)
            if caller["errors"]:
                errors.extend(f"caller claim: {e}" for e in caller["errors"])
            else:
                if not session_id:
                    session_id = str(caller.get("session_id") or "") or None
                if not args.paths:
                    planned = [str(p) for p in caller.get("paths") or []]

    for raw in args.paths:
        safe = safe_relative_path(root, raw)
        if safe is None:
            errors.append(f"unsafe planned path: {raw}")
        else:
            planned.append(safe)

    if not planned and not errors:
        errors.append("no --path provided (and --claim did not supply planned_paths)")

    if errors:
        payload = {
            "read_only": True,
            "trusted_local_filesystem_only": True,
            "is_lock": False,
            "planned_paths": planned,
            "session_id": session_id,
            "active_claim_count": 0,
            "considered_claim_count": 0,
            "conflict_count": 0,
            "conflicts": [],
            "invalid_claim_count": 0,
            "invalid_claims": [],
            "errors": errors,
            "allowed": False,
            "ignore_invalid_claims": args.ignore_invalid_claims,
        }
        print(json.dumps(payload, indent=2))
        return 2

    payload = _run_gate(
        root,
        planned,
        claims_dir=claims_dir,
        session_id=session_id,
        fail_on_expired=args.fail_on_expired,
        ignore_invalid_claims=args.ignore_invalid_claims,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
