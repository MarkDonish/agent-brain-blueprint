from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_vault_structure.py"
SPEC = importlib.util.spec_from_file_location("structure", SCRIPT)
assert SPEC and SPEC.loader
STRUCTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STRUCTURE)


class StructureTests(unittest.TestCase):
    def test_template_vault_passes(self) -> None:
        root = Path(__file__).parents[1] / "templates" / "vault"
        report = STRUCTURE.check_structure(root)
        self.assertEqual(report["failure_count"], 0)

    def test_missing_top_level_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = STRUCTURE.check_structure(Path(directory))
            self.assertGreater(report["failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
