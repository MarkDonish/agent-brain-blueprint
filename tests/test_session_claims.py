from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_session_claims.py"
SPEC = importlib.util.spec_from_file_location("claims", SCRIPT)
assert SPEC and SPEC.loader
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)

sys.path.insert(0, str(ROOT / "scripts"))
import check_claim_gate as GATE_MOD  # noqa: E402


def record(
    paths: list[str],
    *,
    session: str = "one",
    status: str = "active",
    closeout: str = "open",
    expires_at: str | None = "2099-01-01T00:00:00+00:00",
    claimed_by: str = "demo-agent",
) -> str:
    lines = "\n".join(f"  - {path}" for path in paths)
    expires = f"expires_at: {expires_at}\n" if expires_at is not None else ""
    return f"""---
session_id: {session}
task: Test claim
claimed_at: 2026-01-01T00:00:00+00:00
{expires}claimed_by: {claimed_by}
status: {status}
planned_paths:
{lines}
dry_run_status: pending
dry_run_command: test
dry_run_evidence: self-attested test data
closeout_state: {closeout}
closeout_summary: Not closed
next_action: Continue
---
"""


def run_gate(argv: list[str]) -> tuple[int, dict]:
    buf = io.StringIO()
    old = sys.argv
    try:
        sys.argv = argv
        with redirect_stdout(buf):
            code = GATE_MOD.main()
    finally:
        sys.argv = old
    return code, json.loads(buf.getvalue())


class ClaimTests(unittest.TestCase):
    def test_safe_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                CLAIMS.safe_relative_path(root, "10_projects/example/file.md"),
                "10_projects/example/file.md",
            )

    def test_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(CLAIMS.safe_relative_path(Path(directory), "../outside.md"))

    def test_detects_parent_child_overlap(self) -> None:
        self.assertTrue(CLAIMS.overlaps("10_projects/app", "10_projects/app/task.md"))

    def test_valid_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            claim.write_text(record(["10_projects/example/file.md"]), encoding="utf-8")
            result = CLAIMS.claim_result(root, claim)
            self.assertEqual(result["errors"], [])
            self.assertTrue(result["active"])

    def test_rejects_absolute_planned_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            claim.write_text(record(["/tmp/outside.md"]), encoding="utf-8")
            result = CLAIMS.claim_result(root, claim)
            self.assertTrue(any("unsafe planned path" in error for error in result["errors"]))

    def test_closed_status_requires_closed_closeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            claim.write_text(
                record(["10_projects/example/file.md"], status="closed", closeout="open"),
                encoding="utf-8",
            )
            result = CLAIMS.claim_result(root, claim)
            self.assertTrue(
                any("closed status requires closed closeout_state" in error for error in result["errors"])
            )

    def test_expired_claim_not_active(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            # claimed_at before expires_at, both in the past relative to "now"
            body = record(
                ["10_projects/example/file.md"],
                expires_at="2020-06-01T00:00:00+00:00",
            ).replace(
                "claimed_at: 2026-01-01T00:00:00+00:00",
                "claimed_at: 2020-01-01T00:00:00+00:00",
            )
            claim.write_text(body, encoding="utf-8")
            result = CLAIMS.claim_result(root, claim, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
            self.assertEqual(result["errors"], [])
            self.assertFalse(result["active"])
            self.assertTrue(result["expired"])
            self.assertTrue(result["warnings"])

    def test_gate_detects_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            (claims / "a.md").write_text(
                record(["10_projects/example/file.md"], session="a"), encoding="utf-8"
            )
            code, payload = run_gate(
                ["check_claim_gate.py", str(root), "--path", "10_projects/example/file.md"]
            )
            self.assertEqual(code, 2)
            self.assertFalse(payload["allowed"])
            self.assertGreaterEqual(payload["conflict_count"], 1)

    def test_gate_does_not_conflict_with_own_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            (claims / "a.md").write_text(
                record(["10_projects/example/file.md"], session="session-a"),
                encoding="utf-8",
            )
            code, payload = run_gate(
                [
                    "check_claim_gate.py",
                    str(root),
                    "--session-id",
                    "session-a",
                    "--path",
                    "10_projects/example/file.md",
                ]
            )
            self.assertEqual(code, 0, payload)
            self.assertTrue(payload["allowed"])
            self.assertEqual(payload["conflict_count"], 0)

    def test_gate_via_claim_flag_excludes_self(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            claim_rel = "40_handoffs/session_claims/a.md"
            (root / claim_rel).write_text(
                record(["10_projects/example/file.md"], session="session-a"),
                encoding="utf-8",
            )
            code, payload = run_gate(
                ["check_claim_gate.py", str(root), "--claim", claim_rel]
            )
            self.assertEqual(code, 0, payload)
            self.assertTrue(payload["allowed"])
            self.assertEqual(payload["session_id"], "session-a")

    def test_gate_still_conflicts_other_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            (claims / "a.md").write_text(
                record(["10_projects/example/file.md"], session="session-a"),
                encoding="utf-8",
            )
            (claims / "b.md").write_text(
                record(["10_projects/example/file.md"], session="session-b"),
                encoding="utf-8",
            )
            code, payload = run_gate(
                [
                    "check_claim_gate.py",
                    str(root),
                    "--session-id",
                    "session-a",
                    "--path",
                    "10_projects/example/file.md",
                ]
            )
            self.assertEqual(code, 2)
            self.assertFalse(payload["allowed"])
            self.assertGreaterEqual(payload["conflict_count"], 1)

    def test_gate_fails_closed_on_malformed_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            (claims / "bad.md").write_text("not a claim\n", encoding="utf-8")
            code, payload = run_gate(
                ["check_claim_gate.py", str(root), "--path", "10_projects/example/file.md"]
            )
            self.assertEqual(code, 2)
            self.assertFalse(payload["allowed"])
            self.assertGreaterEqual(payload["invalid_claim_count"], 1)
            self.assertIn("invalid_existing_claim", payload["errors"])

    def test_gate_fails_closed_on_unreadable_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            bad = claims / "unreadable.md"
            bad.write_bytes(b"\xff\xfe\x00not-utf8")
            # claim_result reads as utf-8; binary may raise UnicodeError
            code, payload = run_gate(
                ["check_claim_gate.py", str(root), "--path", "10_projects/example/ok.md"]
            )
            self.assertEqual(code, 2)
            self.assertFalse(payload["allowed"])
            self.assertGreaterEqual(payload["invalid_claim_count"], 1)

    def test_gate_ignore_invalid_claims_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            (claims / "bad.md").write_text("not a claim\n", encoding="utf-8")
            code, payload = run_gate(
                [
                    "check_claim_gate.py",
                    str(root),
                    "--path",
                    "10_projects/example/file.md",
                    "--ignore-invalid-claims",
                ]
            )
            self.assertEqual(code, 0, payload)
            self.assertTrue(payload["allowed"])
            self.assertGreaterEqual(payload["invalid_claim_count"], 1)

    def test_expires_at_must_be_after_claimed_at(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            claim.write_text(
                record(
                    ["10_projects/example/file.md"],
                    expires_at="2020-01-01T00:00:00+00:00",
                ).replace(
                    "claimed_at: 2026-01-01T00:00:00+00:00",
                    "claimed_at: 2026-06-01T00:00:00+00:00",
                ),
                encoding="utf-8",
            )
            result = CLAIMS.claim_result(root, claim)
            self.assertTrue(any("expires_at must be after claimed_at" in e for e in result["errors"]))

    def test_blocked_requires_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.md"
            claim.write_text(
                record(["10_projects/example/file.md"], status="blocked"),
                encoding="utf-8",
            )
            result = CLAIMS.claim_result(root, claim)
            self.assertTrue(any("blocked status requires blocker" in e for e in result["errors"]))

    def test_duplicate_active_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claims = root / "40_handoffs" / "session_claims"
            claims.mkdir(parents=True)
            body = record(["10_projects/example/a.md"], session="same-session")
            (claims / "one.md").write_text(body, encoding="utf-8")
            (claims / "two.md").write_text(
                record(["10_projects/example/b.md"], session="same-session"),
                encoding="utf-8",
            )
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            old = sys.argv
            try:
                sys.argv = ["check_session_claims.py", str(root)]
                with redirect_stdout(buf):
                    code = CLAIMS.main()
            finally:
                sys.argv = old
            self.assertEqual(code, 2)
            payload = json.loads(buf.getvalue())
            self.assertGreaterEqual(payload["failure_count"], 1)
            blob = json.dumps(payload)
            self.assertIn("duplicate active session_id", blob)


if __name__ == "__main__":
    unittest.main()
