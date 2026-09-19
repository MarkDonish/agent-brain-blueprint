from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "doctor.py"
SPEC = importlib.util.spec_from_file_location("doctor", SCRIPT)
assert SPEC and SPEC.loader
DOCTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCTOR)


def run_doctor(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    old = sys.argv
    try:
        sys.argv = argv
        with redirect_stdout(buf):
            code = DOCTOR.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


class DoctorTests(unittest.TestCase):
    def test_template_vault_passes(self) -> None:
        code, output = run_doctor(["scripts/doctor.py", str(ROOT / "templates" / "vault")])
        self.assertEqual(code, 0, output)
        report = json.loads(output) if output.lstrip().startswith("{") else None
        if report is not None:
            self.assertEqual(report["failure_count"], 0)

    def test_run_check_reports_failure_for_broken_vault(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = DOCTOR.run_check("check_vault_structure.py", Path(directory))
            self.assertEqual(result["exit_code"], 2)
            payload = result["report"]
            self.assertIsInstance(payload, dict)
            self.assertGreater(payload.get("failure_count", 0), 0)
            self.assertTrue(result["hint"], "failed checks must carry a repair hint")

    def test_run_check_parses_json_report(self) -> None:
        result = DOCTOR.run_check("check_vault_structure.py", ROOT / "templates" / "vault")
        self.assertEqual(result["exit_code"], 0)
        self.assertIsInstance(result["report"], dict)

    def test_summarize_failures_lists_paths(self) -> None:
        report = {
            "failures": [
                {"path": "10_projects/app", "errors": ["missing: 50_decisions"]},
                {"path": "00_entrypoint", "missing": ["SESSION_START_CARD.md"]},
                "not-a-dict",
            ]
            + [{"path": f"extra-{i}"} for i in range(10)]
        }
        lines = DOCTOR.summarize_failures(report)
        self.assertLessEqual(len(lines), 5, "summary is capped at five lines")
        self.assertIn("10_projects/app", lines[0])
        self.assertIn("missing: 50_decisions", lines[0])


if __name__ == "__main__":
    unittest.main()
