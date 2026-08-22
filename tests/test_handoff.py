from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Allow running via bare `python3 -m unittest discover -s tests` without
# relying on the Makefile's PYTHONPATH export.
ROOT = Path(__file__).resolve().parents[1]
for entry in ("src", "scripts"):
    path = str(ROOT / entry)
    if path not in sys.path:
        sys.path.insert(0, path)

from agent_brain.cli.claim_ops import acquire_claim  # noqa: E402
from agent_brain.handoff.engine import create_handoff  # noqa: E402
from agent_brain.session.end import session_end  # noqa: E402


class HandoffEngineTests(unittest.TestCase):
    def test_create_handoff_basic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            proj_dir = vault / "10_projects" / "test-app"
            proj_dir.mkdir(parents=True)

            res = create_handoff(
                vault,
                project="test-app",
                summary="Completed feature X and verified tests.",
                session_id="sess-001",
                completed_tasks=["Implemented feature X", "Added unit tests"],
                evidence=[{"command": "make test", "result": "PASS"}],
                active_decisions=["Use stdio MCP"],
                superseded_decisions=[{"decision": "Old plan", "reason": "Switched to MCP"}],
                next_steps=["Deploy to staging", "Configure monitoring"],
                blockers=["Upstream model rate limits"],
                owner="tester",
            )

            self.assertTrue(res["ok"])
            self.assertEqual(res["tasks_completed_count"], 2)
            self.assertEqual(res["evidence_count"], 1)
            self.assertEqual(res["active_decisions_count"], 1)
            self.assertEqual(res["superseded_decisions_count"], 1)
            self.assertEqual(res["next_steps_count"], 2)
            self.assertEqual(res["blockers_count"], 1)

            created_file = vault / res["path"]
            self.assertTrue(created_file.is_file())
            content = created_file.read_text(encoding="utf-8")
            self.assertIn("memory_type: handoff", content)
            self.assertIn("## 1. 🎯 30-Second Status & Summary", content)
            self.assertIn("Completed feature X and verified tests.", content)
            self.assertIn("- [x] Implemented feature X", content)
            self.assertIn("| 1 | `make test` | PASS |", content)
            self.assertIn("✅ **[Active]** Use stdio MCP", content)
            self.assertIn("🚫 **[Superseded]** Old plan — *Reason*: Switched to MCP", content)
            self.assertIn("- [ ] **P0**: Deploy to staging", content)
            self.assertIn("- ⚠️ Upstream model rate limits", content)

    def test_create_handoff_closes_claim(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            proj_dir = vault / "10_projects" / "claim-app"
            proj_dir.mkdir(parents=True)

            claim_file = acquire_claim(
                vault,
                session_id="sess-claim",
                task="Feature work",
                planned_paths=["10_projects/claim-app/10_current_work/INDEX.md"],
                claimed_by="tester",
            )
            self.assertTrue(claim_file.is_file())

            res = create_handoff(
                vault,
                project="claim-app",
                summary="Work done and claim closed.",
                session_id="sess-claim",
                close_claim_file=True,
                owner="tester",
            )
            self.assertTrue(res["ok"])
            self.assertEqual(len(res["closed_claims"]), 1)

            claim_content = claim_file.read_text(encoding="utf-8")
            self.assertIn("status: closed", claim_content)
            self.assertIn("Work done and claim closed.", claim_content)

    def test_create_handoff_chinese_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            proj_dir = vault / "10_项目工作区" / "测试项目"
            proj_dir.mkdir(parents=True)

            res = create_handoff(
                vault,
                project="测试项目",
                summary="测试中文路径下的智能交接",
                session_id="sess-cjk",
                owner="mark",
            )
            self.assertTrue(res["ok"])
            created_file = vault / res["path"]
            self.assertTrue(created_file.is_file())
            self.assertIn("10_项目工作区/测试项目/20_交接记录", res["path"])

    def test_session_end_integration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            proj_dir = vault / "10_projects" / "int-app"
            proj_dir.mkdir(parents=True)

            res = session_end(
                vault,
                project="int-app",
                session_id="sess-int",
                handoff_summary="End of session handoff",
                completed_tasks=["Task 1", "Task 2"],
                evidence=[{"command": "pytest", "result": "PASS"}],
                write_handoff=True,
                owner="tester",
            )

            self.assertEqual(res["phase"], "session_end")
            actions = res["actions"]
            self.assertTrue(any(a["type"] == "handoff_written" for a in actions))


if __name__ == "__main__":
    unittest.main()
