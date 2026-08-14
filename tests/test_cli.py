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


class CliTests(unittest.TestCase):
    def test_init_doctor_project_claim_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            proc = run_cli("init", "--destination", str(vault), "--project", "demo-app")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertTrue((vault / ".agent-brain" / "manifest.json").is_file())
            self.assertTrue((vault / "10_projects" / "demo-app" / "PROJECT_OVERVIEW.md").is_file())

            proc = run_cli("doctor", str(vault))
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

            proc = run_cli("project", "list", str(vault))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("demo-app", proc.stdout)
            # bootstrap also leaves example-app from template
            self.assertIn("example-app", proc.stdout)

            proc = run_cli(
                "project",
                "add",
                str(vault),
                "--name",
                "second-app",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((vault / "10_projects" / "second-app" / "PROJECT_OVERVIEW.md").is_file())

            proc = run_cli(
                "claim",
                "acquire",
                str(vault),
                "--session-id",
                "cli-test-session",
                "--task",
                "touch current work",
                "--path",
                "10_projects/demo-app/10_current_work/INDEX.md",
                "--filename",
                "cli-test-claim.md",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            claim = vault / "40_handoffs" / "session_claims" / "cli-test-claim.md"
            self.assertTrue(claim.is_file())

            # Owner gate should allow
            proc = run_cli(
                "claim",
                "gate",
                str(vault),
                "--claim",
                "40_handoffs/session_claims/cli-test-claim.md",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["allowed"])

            # Foreign gate conflicts
            proc = run_cli(
                "claim",
                "gate",
                str(vault),
                "--path",
                "10_projects/demo-app/10_current_work/INDEX.md",
            )
            self.assertEqual(proc.returncode, 2)
            payload = json.loads(proc.stdout)
            self.assertFalse(payload["allowed"])

            proc = run_cli(
                "claim",
                "close",
                str(vault),
                "--claim",
                "40_handoffs/session_claims/cli-test-claim.md",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = claim.read_text(encoding="utf-8")
            self.assertIn("status: closed", text)
            self.assertIn("closeout_state: closed", text)

            proc = run_cli("claim", "status", str(vault))
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

    def test_project_add_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            self.assertEqual(run_cli("init", "--destination", str(vault)).returncode, 0)
            proc = run_cli("project", "add", str(vault), "--name", "../outside")
            self.assertNotEqual(proc.returncode, 0)

    def test_record_id(self) -> None:
        proc = run_cli("record", "id", "--prefix", "mem")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.strip().startswith("mem_"))

    def test_memory_help(self) -> None:
        proc = run_cli("memory", "--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("promote", proc.stdout)

    def test_privacy_scan_repo(self) -> None:
        proc = run_cli("privacy", str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["secret_finding_count"], 0)

    def test_claim_renew_and_prune(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            self.assertEqual(run_cli("init", "--destination", str(vault)).returncode, 0)

            proc = run_cli(
                "claim",
                "acquire",
                str(vault),
                "--session-id",
                "renew-test",
                "--task",
                "test renew",
                "--path",
                "10_projects/example-app/10_current_work/INDEX.md",
                "--filename",
                "renew-claim.md",
                "--hours",
                "1",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            renew_proc = run_cli(
                "claim",
                "renew",
                str(vault),
                "--claim",
                "40_handoffs/session_claims/renew-claim.md",
                "--hours",
                "12",
            )
            self.assertEqual(renew_proc.returncode, 0, renew_proc.stderr)

            prune_proc = run_cli("claim", "prune", str(vault), "--dry-run", "--json")
            self.assertEqual(prune_proc.returncode, 0, prune_proc.stderr)
            self.assertEqual(json.loads(prune_proc.stdout), [])

    def test_mcp_help(self) -> None:
        proc = run_cli("mcp", "--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Model Context Protocol", proc.stdout)


if __name__ == "__main__":
    unittest.main()
