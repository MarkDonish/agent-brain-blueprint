from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_vault_structure.py"
SPEC = importlib.util.spec_from_file_location("structure", SCRIPT)
assert SPEC and SPEC.loader
STRUCTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STRUCTURE)

sys.path.insert(0, str(ROOT / "scripts"))
import fix_vault_structure as FIX  # noqa: E402


class StructureTests(unittest.TestCase):
    def test_template_vault_passes(self) -> None:
        root = ROOT / "templates" / "vault"
        report = STRUCTURE.check_structure(root)
        self.assertEqual(report["failure_count"], 0, report)

    def test_missing_top_level_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = STRUCTURE.check_structure(Path(directory))
            self.assertGreater(report["failure_count"], 0)

    def test_gitkeep_created_as_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = FIX.missing_entries(root)
            FIX.apply(missing)
            gitkeep = root / "40_handoffs" / "session_claims" / ".gitkeep"
            self.assertTrue(gitkeep.is_file())
            self.assertFalse(gitkeep.is_dir())
            report = STRUCTURE.check_structure(root)
            # AGENTS.md and other placeholders may still be incomplete content-wise
            # but kinds should match; SESSION_START_CARD and AGENTS are files.
            gitkeep_failures = [
                f
                for f in report["failures"]
                if "session_claims/.gitkeep" in str(f.get("path", ""))
            ]
            self.assertEqual(gitkeep_failures, [])

    def test_required_file_cannot_be_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Create AGENTS.md as a directory (wrong kind)
            (root / "AGENTS.md").mkdir(parents=True)
            report = STRUCTURE.check_structure(root)
            self.assertTrue(
                any(
                    "required file is a directory" in err
                    for f in report["failures"]
                    for err in f.get("errors", [])
                ),
                report,
            )

    def test_required_directory_cannot_be_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "10_projects").write_text("not a dir\n", encoding="utf-8")
            report = STRUCTURE.check_structure(root)
            self.assertTrue(
                any(
                    "required directory is a file" in err
                    for f in report["failures"]
                    for err in f.get("errors", [])
                ),
                report,
            )


if __name__ == "__main__":
    unittest.main()
