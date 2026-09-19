from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from agent_brain.retrieval.index import (  # noqa: E402
    check_index,
    default_index_path,
    rebuild_index,
    refresh_index,
    status_index,
)
from agent_brain.retrieval.query import search  # noqa: E402


def make_vault(root: Path, *, chinese: bool = False) -> Path:
    vault = root / "vault"
    if chinese:
        (vault / "00_入口").mkdir(parents=True)
        (vault / "10_项目工作区" / "项目甲" / "10_当前任务").mkdir(parents=True)
        (vault / "00_入口" / "06_Agent会话加载卡.md").write_text("# 会话加载卡\n读取项目甲", encoding="utf-8")
        (vault / "10_项目工作区" / "项目甲" / "00_项目总览.md").write_text("# 项目甲\n中文检索", encoding="utf-8")
    else:
        (vault / "00_entrypoint").mkdir(parents=True)
        (vault / "10_projects" / "app" / "10_current_work").mkdir(parents=True)
        (vault / "00_entrypoint" / "SESSION_START_CARD.md").write_text("# Session\nload card", encoding="utf-8")
        (vault / "10_projects" / "app" / "PROJECT_OVERVIEW.md").write_text("# App\ncanonical source", encoding="utf-8")
    (vault / "AGENTS.md").write_text("# rules", encoding="utf-8")
    return vault


class IndexGenerationTests(unittest.TestCase):
    def test_first_rebuild_current_status_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            report = rebuild_index(vault)
            pointer = vault / "50_retrieval" / "indexes" / "current.json"
            self.assertTrue(pointer.is_file())
            self.assertEqual(json.loads(pointer.read_text())["generation_id"], report["generation_id"])
            self.assertIn(report["generation_id"], str(default_index_path(vault)))
            status = status_index(vault)
            self.assertEqual((status["missing_source_count"], status["stale_source_count"]), (0, 0))
            self.assertTrue(status["coverage_complete"])
            self.assertTrue(check_index(vault)["passed"])

    def test_refresh_added_modified_deleted_and_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            first = rebuild_index(vault)
            added = vault / "10_projects" / "app" / "10_current_work" / "new.md"
            added.write_text("# New\nadded term", encoding="utf-8")
            refresh = refresh_index(vault)
            self.assertEqual(refresh["added"], 1)
            self.assertNotEqual(first["generation_id"], refresh["generation_id"])
            added.write_text("# New\nmodified term", encoding="utf-8")
            modified = refresh_index(vault)
            self.assertEqual(modified["modified"], 1)
            added.unlink()
            deleted = refresh_index(vault)
            self.assertEqual(deleted["deleted"], 1)
            noop = refresh_index(vault)
            self.assertTrue(noop["no_op"])
            self.assertFalse(noop["published"])

    def test_failed_build_keeps_current_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            first = rebuild_index(vault)
            before = search(vault, "canonical source")
            (vault / "10_projects" / "app" / "PROJECT_OVERVIEW.md").write_text("# App\nnew only", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                rebuild_index(vault, failure_at="before_publish")
            self.assertEqual(status_index(vault)["generation_id"], first["generation_id"])
            after = search(vault, "canonical source")
            self.assertEqual([h["path"] for h in before["hits"]], [h["path"] for h in after["hits"]])

    def test_lock_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            lock = vault / "50_retrieval" / "indexes" / ".build.lock"
            lock.mkdir(parents=True)
            with self.assertRaises(TimeoutError):
                rebuild_index(vault, lock_timeout=0)

    def test_corrupt_manifest_and_sqlite_fail_check(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            rebuild_index(vault)
            index = default_index_path(vault)
            manifest = index.parent / "manifest.json"
            manifest.write_text("{bad", encoding="utf-8")
            self.assertFalse(check_index(vault)["passed"])
            # Rebuild a healthy generation, then corrupt only SQLite.
            rebuild_index(vault)
            default_index_path(vault).write_bytes(b"not sqlite")
            self.assertFalse(check_index(vault)["passed"])

    def test_cursor_pagination_and_generation_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td))
            for i in range(4):
                (vault / "10_projects" / "app" / "10_current_work" / f"r{i}.md").write_text(f"# R{i}\nterm", encoding="utf-8")
            rebuild_index(vault)
            first = search(vault, "term", limit=2)
            second = search(vault, "term", limit=2, cursor=first["next_cursor"])
            paths = [item["path"] for item in first["hits"] + second["hits"]]
            self.assertEqual(len(paths), len(set(paths)))
            old_cursor = first["next_cursor"]
            rebuild_index(vault)
            rejected = search(vault, "term", limit=2, cursor=old_cursor)
            self.assertFalse(rejected["ok"])
            self.assertIn("generation", rejected["error"])

    def test_chinese_layout_and_navigation_weight(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_vault(Path(td), chinese=True)
            report = rebuild_index(vault)
            self.assertEqual(status_index(vault)["layout_id"], "agent-brain-zh-v1")
            self.assertTrue(search(vault, "会话加载卡", detail="scout")["hits"][0]["path"].startswith("00_入口"))
            self.assertEqual(report["blocked_source_count"], 0)


if __name__ == "__main__":
    unittest.main()
