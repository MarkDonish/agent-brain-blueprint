from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_privacy_scan.py"
SPEC = importlib.util.spec_from_file_location("privacy", SCRIPT)
assert SPEC and SPEC.loader
PRIVACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIVACY)


def _private_key_fixture() -> str:
    # Build at runtime so the test source does not contain a literal key block.
    return "-----BEGIN " + "PRIVATE KEY-----\nABCD\n-----END " + "PRIVATE KEY-----\n"


def _home(rest: str) -> str:
    # Build home paths at runtime so the test source itself stays scan-clean.
    return "/" + "/".join(["Users", *rest.split("/")])


def _home_path_fixture() -> str:
    return "vault lives at " + _home("demo/secret-vault") + "\n"


def _openai_key_fixture() -> str:
    # sk- + 20+ alnum
    return "token = " + "sk-" + ("a" * 24) + "\n"


def _bearer_fixture() -> str:
    return "Authorization: Bearer " + ("Z" * 32) + "\n"


def _run_main(root, *extra: str) -> tuple[int, str]:
    buf = io.StringIO()
    argv = ["check_privacy_scan.py", str(root), *extra]
    old = sys.argv
    try:
        sys.argv = argv
        with redirect_stdout(buf):
            code = PRIVACY.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


class PrivacyScanTests(unittest.TestCase):
    def test_repo_checkout_has_no_secret_hits(self) -> None:
        root = Path(__file__).parents[1]
        report = PRIVACY.scan(root)
        self.assertEqual(report["secret_finding_count"], 0, report["secret_findings"])
        # The public checkout must stay clean enough for `--strict` in CI.
        self.assertEqual(report["risk_finding_count"], 0, report["risk_findings"])

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
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "path.md"
            sample.write_text(_home_path_fixture(), encoding="utf-8")
            report = PRIVACY.scan(root)
            self.assertGreaterEqual(report["checked_file_count"], 1)
            self.assertGreaterEqual(report["risk_finding_count"], 1)

    def test_allowlist_suppresses_only_matching_risk_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".privacy-allowlist").write_text("demo-user\n", encoding="utf-8")
            sample = root / "notes.md"
            sample.write_text(
                "contact demo-user@example-app.dev\n" + "root lives at " + _home("demo/secret-vault") + "\n",
                encoding="utf-8",
            )
            report = PRIVACY.scan(root)
            self.assertEqual(report["secret_finding_count"], 0)
            emails = [item for item in report["risk_findings"] if item["severity"] == "email"]
            self.assertEqual(emails, [], "allowlisted email match should be suppressed")
            paths = [item for item in report["risk_findings"] if item["severity"] == "home_path"]
            self.assertEqual(len(paths), 1, "unrelated home path must still be reported")
            self.assertIn(_home("demo"), str(paths[0]["detail"]))

    def test_risk_on_same_line_as_allowlisted_text_still_reported(self) -> None:
        # Line-level allowlisting used to hide leaks that shared a line with
        # an allowlisted placeholder. Suppression is match-level now.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "notes.md"
            sample.write_text("user demo-user lives at " + _home("jane/secret-vault") + "\n", encoding="utf-8")
            report = PRIVACY.scan(root)
            self.assertEqual(report["secret_finding_count"], 0)
            self.assertGreaterEqual(report["risk_finding_count"], 1)

    def test_strict_mode_fails_on_risk_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "path.md").write_text(_home_path_fixture(), encoding="utf-8")
            code, _ = _run_main(root, "--strict")
            self.assertEqual(code, 2)

    def test_non_strict_mode_ignores_risk_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "path.md").write_text(_home_path_fixture(), encoding="utf-8")
            code, _ = _run_main(root)
            self.assertEqual(code, 0)

    def test_secret_output_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_key = "sk-" + ("b" * 24)
            (root / "leak.md").write_text(f"key={raw_key}\n", encoding="utf-8")
            report = PRIVACY.scan(root)
            dumped = json.dumps(report)
            self.assertGreaterEqual(report["secret_finding_count"], 1)
            self.assertNotIn(raw_key, dumped)
            detail = report["secret_findings"][0]["detail"]
            self.assertIn("[REDACTED]", detail)
            self.assertIn("fingerprint", report["secret_findings"][0])

    def test_bearer_token_never_appears_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = "Z" * 32
            (root / "auth.md").write_text(f"Authorization: Bearer {token}\n", encoding="utf-8")
            report = PRIVACY.scan(root)
            dumped = json.dumps(report)
            self.assertGreaterEqual(report["secret_finding_count"], 1)
            self.assertNotIn(token, dumped)
            self.assertNotIn(f"Bearer {token}", dumped)

    def test_openai_key_never_appears_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = "sk-" + ("c" * 24)
            (root / "env.md").write_text(_openai_key_fixture().replace("sk-" + ("a" * 24), key), encoding="utf-8")
            report = PRIVACY.scan(root)
            dumped = json.dumps(report)
            self.assertGreaterEqual(report["secret_finding_count"], 1)
            self.assertNotIn(key, dumped)


if __name__ == "__main__":
    unittest.main()
