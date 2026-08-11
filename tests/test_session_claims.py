from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_session_claims.py"
SPEC = importlib.util.spec_from_file_location("claims", SCRIPT)
assert SPEC and SPEC.loader
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)


def record(paths: list[str], session: str = "one") -> str:
    lines = "\n".join(f"  - {path}" for path in paths)
    return f"""---
session_id: {session}
task: Test claim
claimed_at: 2026-01-01T00:00:00+00:00
status: active
planned_paths:
{lines}
dry_run_status: pending
dry_run_command: test
dry_run_evidence: self-attested test data
closeout_state: open
closeout_summary: Not closed
next_action: Continue
---
"""


class ClaimTests(unittest.TestCase):
    def test_safe_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(CLAIMS.safe_relative_path(root, "10_projects/example/file.md"), "10_projects/example/file.md")

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


if __name__ == "__main__":
    unittest.main()
