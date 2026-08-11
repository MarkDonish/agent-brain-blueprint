from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_memory_governance.py"
SPEC = importlib.util.spec_from_file_location("governance", SCRIPT)
assert SPEC and SPEC.loader
GOVERNANCE = importlib.util.module_from_spec(SPEC)
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
            self.assertEqual(list(GOVERNANCE.governed_files(root)), [])

    def test_decision_record_is_governed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root / "30_global_decisions"
            decisions.mkdir()
            record = decisions / "decision.md"
            record.write_text("# Missing frontmatter\n", encoding="utf-8")
            self.assertEqual(list(GOVERNANCE.governed_files(root)), [record])


if __name__ == "__main__":
    unittest.main()
