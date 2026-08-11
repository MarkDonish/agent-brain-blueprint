from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_memory_governance.py"
SPEC = importlib.util.spec_from_file_location("governance", SCRIPT)
assert SPEC and SPEC.loader
GOVERNANCE = importlib.util.module_from_spec(SPEC)
import sys

sys.modules["governance"] = GOVERNANCE
# allow scripts/lib imports
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
SPEC.loader.exec_module(GOVERNANCE)


class GovernanceTests(unittest.TestCase):
    def test_directory_readme_and_index_are_not_governed_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root / "30_global_decisions"
            decisions.mkdir()
            (decisions / "README.md").write_text("# Directory guide\n", encoding="utf-8")
            (decisions / "INDEX.md").write_text("# Directory index\n", encoding="utf-8")
            project_decisions = root / "10_projects" / "example-app" / "50_decisions"
            project_decisions.mkdir(parents=True)
            (project_decisions / "README.md").write_text("# Project guide\n", encoding="utf-8")
            (project_decisions / "INDEX.md").write_text("# Project index\n", encoding="utf-8")
            targets = list(GOVERNANCE.iter_targets(root, include_soft=True))
            self.assertEqual(targets, [])

    def test_decision_record_is_governed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root / "30_global_decisions"
            decisions.mkdir()
            record = decisions / "decision.md"
            record.write_text("# Missing frontmatter\n", encoding="utf-8")
            targets = list(GOVERNANCE.iter_targets(root, include_soft=False))
            self.assertEqual([path for path, _, _ in targets], [record])
            result = GOVERNANCE.check_file(root, record, "memory_record", "strict")
            self.assertTrue(result["errors"])

    def test_complete_decision_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root / "30_global_decisions"
            decisions.mkdir()
            record = decisions / "decision.md"
            record.write_text(
                """---
memory_type: decision
source: test
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2026-02-01
owner: demo-user
---
# ok
""",
                encoding="utf-8",
            )
            result = GOVERNANCE.check_file(root, record, "memory_record", "strict")
            self.assertEqual(result["errors"], [])

    def test_production_risk_requires_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root / "30_global_decisions"
            decisions.mkdir()
            record = decisions / "decision.md"
            record.write_text(
                """---
memory_type: decision
source: test
confidence: pending
freshness: current
scope: project
risk_boundary: production
next_review: 2026-02-01
owner: demo-user
---
# risky
""",
                encoding="utf-8",
            )
            result = GOVERNANCE.check_file(root, record, "memory_record", "strict")
            self.assertTrue(
                any("production risk_boundary requires confidence=verified" in e for e in result["errors"])
            )

    def test_validation_pass_needs_evidence_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "10_projects" / "app" / "40_validation" / "v.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                """---
memory_type: validation
status: pass
owner: demo-user
---
# bare pass
""",
                encoding="utf-8",
            )
            result = GOVERNANCE.check_file(root, path, "validation", "soft")
            self.assertEqual(result["errors"], [])
            self.assertTrue(any("commands or evidence_ref" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
