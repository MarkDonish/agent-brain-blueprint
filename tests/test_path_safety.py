from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "lib" / "path_safety.py"
SPEC = importlib.util.spec_from_file_location("path_safety", SCRIPT)
assert SPEC and SPEC.loader
PS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PS)


class PathSafetyTests(unittest.TestCase):
    def test_project_accepts_valid_slug(self) -> None:
        self.assertEqual(PS.validate_project_slug("example-app"), "example-app")
        self.assertEqual(PS.validate_project_slug("Demo_Notes.App"), "Demo_Notes.App")

    def test_project_rejects_parent_escape(self) -> None:
        with self.assertRaises(PS.PathSafetyError):
            PS.validate_project_slug("../../outside")
        with self.assertRaises(PS.PathSafetyError):
            PS.validate_project_slug("../foo")

    def test_project_rejects_absolute_path(self) -> None:
        with self.assertRaises(PS.PathSafetyError):
            PS.validate_project_slug("/tmp/foo")
        with self.assertRaises(PS.PathSafetyError):
            PS.validate_project_slug("~/vault")

    def test_project_rejects_backslash_escape(self) -> None:
        with self.assertRaises(PS.PathSafetyError):
            PS.validate_project_slug("foo\\bar")

    def test_safe_relative_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(PS.safe_relative_path(root, "../outside.md"))
            self.assertIsNone(PS.safe_relative_path(root, "/tmp/x"))
            self.assertEqual(
                PS.safe_relative_path(root, "10_projects/app/file.md"),
                "10_projects/app/file.md",
            )


if __name__ == "__main__":
    unittest.main()
