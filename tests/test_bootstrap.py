from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("bootstrap", SCRIPT)
assert SPEC and SPEC.loader
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOTSTRAP)


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_creates_structure_and_templates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "vault"
            result = BOOTSTRAP.bootstrap(destination)
            self.assertTrue((destination / "00_entrypoint" / "SESSION_START_CARD.md").exists())
            self.assertTrue((destination / "70_inbox" / "README.md").exists())
            self.assertTrue((destination / "80_sensitive_isolation" / "README.md").exists())
            self.assertTrue((destination / "AGENTS.md").exists())
            self.assertTrue((destination / ".gitignore").exists())
            self.assertTrue((destination / "60_templates" / "session_claim.md").exists())
            self.assertTrue((destination / "60_templates" / "memory_record.md").exists())
            self.assertTrue((destination / "10_projects" / "example-app" / "50_decisions" / "INDEX.md").exists())
            self.assertIn("session_claim.md", result["copied_record_templates"])

    def test_bootstrap_refuses_non_empty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "vault"
            destination.mkdir()
            (destination / "already.txt").write_text("nope\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                BOOTSTRAP.bootstrap(destination)


if __name__ == "__main__":
    unittest.main()
