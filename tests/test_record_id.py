from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "lib" / "record_id.py"
SPEC = importlib.util.spec_from_file_location("record_id", SCRIPT)
assert SPEC and SPEC.loader
RID = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RID)


class RecordIdTests(unittest.TestCase):
    def test_generate_stable_with_fixed_entropy(self) -> None:
        a = RID.new_record_id("mem", timestamp_ms=1700000000000, entropy=bytes(range(10)))
        b = RID.new_record_id("mem", timestamp_ms=1700000000000, entropy=bytes(range(10)))
        self.assertEqual(a, b)
        self.assertTrue(RID.is_valid_record_id(a))
        self.assertTrue(a.startswith("mem_"))
        self.assertEqual(len(a.split("_", 1)[1]), 26)

    def test_rejects_invalid_shape(self) -> None:
        self.assertFalse(RID.is_valid_record_id("not-an-id"))
        self.assertFalse(RID.is_valid_record_id("mem_short"))
        self.assertFalse(RID.is_valid_record_id("MEM_01HF7YAT00000G40R40M30E209"))


if __name__ == "__main__":
    unittest.main()
