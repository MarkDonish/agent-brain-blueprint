from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


import sys

ROOT = Path(__file__).parents[1]
LIB = ROOT / "scripts" / "lib" / "frontmatter.py"
SPEC = importlib.util.spec_from_file_location("frontmatter", LIB)
assert SPEC and SPEC.loader
FM = importlib.util.module_from_spec(SPEC)
sys.modules["frontmatter"] = FM
SPEC.loader.exec_module(FM)


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_and_lists(self) -> None:
        text = """---
session_id: one
status: active
planned_paths:
  - 10_projects/example/file.md
  - 10_projects/example/other.md
flag: true
count: 3
---
body
"""
        result = FM.parse_frontmatter(text)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.data["session_id"], "one")
        self.assertEqual(result.data["planned_paths"], ["10_projects/example/file.md", "10_projects/example/other.md"])
        self.assertIs(result.data["flag"], True)
        self.assertEqual(result.data["count"], 3)
        self.assertIn("body", result.body)

    def test_duplicate_key(self) -> None:
        text = """---
a: 1
a: 2
---
"""
        result = FM.parse_frontmatter(text)
        self.assertTrue(any("duplicate field" in err.message for err in result.errors))

    def test_missing_frontmatter(self) -> None:
        result = FM.parse_frontmatter("no frontmatter\n")
        self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
