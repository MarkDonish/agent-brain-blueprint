from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Every shipped vault carries its own AGENTS.md so vaults stay self-contained
# (check_vault_structure requires it). The copies must never drift apart.
AGENTS_MD_COPIES = (
    ROOT / "AGENTS.md",
    ROOT / "templates" / "vault" / "AGENTS.md",
    ROOT / "examples" / "demo-vault" / "AGENTS.md",
)


class AgentsSyncTests(unittest.TestCase):
    def test_agents_md_copies_are_identical(self) -> None:
        for path in AGENTS_MD_COPIES:
            self.assertTrue(path.is_file(), f"missing copy: {path}")
        reference = AGENTS_MD_COPIES[0].read_bytes()
        for path in AGENTS_MD_COPIES[1:]:
            self.assertEqual(
                path.read_bytes(),
                reference,
                f"{path} drifted from the repo root AGENTS.md; "
                "update all copies together (see tests/test_agents_sync.py)",
            )


if __name__ == "__main__":
    unittest.main()
