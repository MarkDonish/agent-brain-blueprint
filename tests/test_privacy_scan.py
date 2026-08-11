from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_privacy_scan.py"
SPEC = importlib.util.spec_from_file_location("privacy", SCRIPT)
assert SPEC and SPEC.loader
PRIVACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIVACY)


def _private_key_fixture() -> str:
    # Build at runtime so the test source does not contain a literal key block.
    return "-----BEGIN " + "PRIVATE KEY-----\nABCD\n-----END " + "PRIVATE KEY-----\n"


def _home_path_fixture() -> str:
    return "vault lives at " + "/" + "/".join(["Users", "demo", "secret-vault"]) + "\n"


class PrivacyScanTests(unittest.TestCase):
    def test_repo_checkout_has_no_secret_hits(self) -> None:
        root = Path(__file__).parents[1]
        report = PRIVACY.scan(root)
        self.assertEqual(report["secret_finding_count"], 0, report["secret_findings"])

    def test_detects_private_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "leak.md"
            sample.write_text(_private_key_fixture(), encoding="utf-8")
            report = PRIVACY.scan(root)
            self.assertGreaterEqual(report["secret_finding_count"], 1)

    def test_detects_home_path_as_risk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "path.md"
            sample.write_text(_home_path_fixture(), encoding="utf-8")
            report = PRIVACY.scan(root)
            self.assertEqual(report["secret_finding_count"], 0)
            self.assertGreaterEqual(report["risk_finding_count"], 1)

    def test_does_not_skip_macos_private_tmp_prefix(self) -> None:
        # Regression: skipping absolute path parts named "private" hid /private/tmp.
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            sample = root / "path.md"
            sample.write_text(_home_path_fixture(), encoding="utf-8")
            report = PRIVACY.scan(root)
            self.assertGreaterEqual(report["checked_file_count"], 1)
            self.assertGreaterEqual(report["risk_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
