from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"


def env_with_src() -> dict[str, str]:
    env = os.environ.copy()
    parts = [str(SRC), str(SCRIPTS)]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(parts + ([existing] if existing else []))
    return env


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agent_brain", *args],
        cwd=str(ROOT),
        env=env_with_src(),
        capture_output=True,
        text=True,
        check=False,
    )


class MemoryOpsTests(unittest.TestCase):
    def test_promote_supersede_review_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            init = run_cli("init", "--destination", str(vault), "--project", "app")
            self.assertEqual(init.returncode, 0, init.stderr)

            promote = run_cli(
                "memory",
                "promote",
                str(vault),
                "--project",
                "app",
                "--title",
                "Rate limit password reset",
                "--conclusion",
                "Password reset must fail closed after 5 attempts per hour.",
                "--source",
                "security review session",
                "--confidence",
                "verified",
            )
            self.assertEqual(promote.returncode, 0, promote.stderr + promote.stdout)
            payload = json.loads(promote.stdout)
            self.assertEqual(payload["action"], "promote")
            self.assertTrue(payload["record_id"].startswith("mem_"))
            path = vault / payload["path"]
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn("state: active", text)
            self.assertIn("Rate limit password reset", text)

            # production without verified fails
            bad = run_cli(
                "memory",
                "promote",
                str(vault),
                "--project",
                "app",
                "--title",
                "Dangerous",
                "--conclusion",
                "Ship without tests",
                "--source",
                "guess",
                "--confidence",
                "pending",
                "--risk-boundary",
                "production",
            )
            self.assertNotEqual(bad.returncode, 0)

            old_id = payload["record_id"]
            sup = run_cli(
                "memory",
                "supersede",
                str(vault),
                "--record-id",
                old_id,
                "--title",
                "Rate limit is 10 per hour",
                "--conclusion",
                "Raise limit to 10 attempts per hour after load test.",
                "--source",
                "load test report",
            )
            self.assertEqual(sup.returncode, 0, sup.stderr + sup.stdout)
            sup_payload = json.loads(sup.stdout)
            self.assertEqual(sup_payload["old_state"], "superseded")
            old_text = path.read_text(encoding="utf-8")
            self.assertIn("state: superseded", old_text)
            new_path = vault / sup_payload["new_path"]
            self.assertTrue(new_path.is_file())
            self.assertIn(old_id, new_path.read_text(encoding="utf-8"))

            # force review due by rewriting next_review
            due_file = vault / "10_projects" / "app" / "50_decisions" / "old-review.md"
            due_file.write_text(
                """---
memory_type: decision
title: Needs review
source: test
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2020-01-01
review_after: 2020-01-01
owner: demo
state: active
record_id: mem_01HF7YAT00000G40R40M30E209
---
# Needs review
""",
                encoding="utf-8",
            )
            review = run_cli("memory", "review", str(vault), "--project", "app")
            self.assertEqual(review.returncode, 0, review.stderr)
            rev = json.loads(review.stdout)
            self.assertGreaterEqual(rev["due_count"], 1)

            start = run_cli(
                "session",
                "start",
                str(vault),
                "--project",
                "app",
                "--task",
                "fix rate limit",
                "--json",
                "--meta-only",
            )
            self.assertEqual(start.returncode, 0, start.stderr + start.stdout)
            start_payload = json.loads(start.stdout)
            self.assertEqual(start_payload["phase"], "session_start")
            self.assertFalse(start_payload["auto_executes"])

            acquire = run_cli(
                "claim",
                "acquire",
                str(vault),
                "--session-id",
                "end-test",
                "--task",
                "wrap up",
                "--path",
                "10_projects/app/10_current_work/INDEX.md",
                "--filename",
                "end-claim.md",
            )
            self.assertEqual(acquire.returncode, 0, acquire.stderr)
            end = run_cli(
                "session",
                "end",
                str(vault),
                "--project",
                "app",
                "--session-id",
                "end-test",
                "--claim",
                "40_handoffs/session_claims/end-claim.md",
                "--close-claim",
                "--write-handoff",
                "--handoff-summary",
                "Closed rate-limit work for the day.",
            )
            self.assertEqual(end.returncode, 0, end.stderr + end.stdout)
            end_payload = json.loads(end.stdout)
            self.assertFalse(end_payload["auto_promotes_memory"])
            claim_text = (vault / "40_handoffs" / "session_claims" / "end-claim.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("status: closed", claim_text)
            self.assertTrue(any(a["type"] == "handoff_written" for a in end_payload["actions"]))

    def test_version_0_9(self) -> None:
        proc = run_cli("--version")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0.9.0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
