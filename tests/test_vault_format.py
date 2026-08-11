from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "check_vault_format.py"
SPEC = importlib.util.spec_from_file_location("vault_format_check", SCRIPT)
assert SPEC and SPEC.loader
FMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FMT)

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from lib.vault_format import write_manifest  # noqa: E402


class VaultFormatTests(unittest.TestCase):
    def test_template_has_manifest(self) -> None:
        report = FMT.check_format(ROOT / "templates" / "vault", require_manifest=True)
        self.assertEqual(report["failure_count"], 0, report)
        self.assertTrue(report["manifest_present"])

    def test_missing_manifest_warns_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = FMT.check_format(Path(directory), require_manifest=False)
            self.assertEqual(report["failure_count"], 0)
            self.assertGreaterEqual(report["warning_count"], 1)

    def test_missing_manifest_fails_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = FMT.check_format(Path(directory), require_manifest=True)
            self.assertGreaterEqual(report["failure_count"], 1)

    def test_unsupported_version_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_manifest(root)
            path = root / ".agent-brain" / "manifest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["vault_format_version"] = 99
            path.write_text(json.dumps(data), encoding="utf-8")
            report = FMT.check_format(root, require_manifest=True)
            self.assertGreaterEqual(report["failure_count"], 1)


if __name__ == "__main__":
    unittest.main()
