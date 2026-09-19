from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_brain.context.builder import build_context
from agent_brain.cli.claim_ops import acquire_claim
from agent_brain.cli.project_ops import add_project
from agent_brain.memory.promote import promote_memory
from agent_brain.memory.review import list_review_due
from agent_brain.retrieval.scan import scan_records
from agent_brain.session.start import session_start
from agent_brain.cli.project_ops import list_projects

from scripts.lib.vault_layout import LayoutDetectionError, detect_layout


def make_zh_vault(root: Path) -> Path:
    """Create the smallest complete Chinese-layout fixture used by adapters."""
    for rel in (
        "00_入口",
        "10_项目工作区",
        "20_Agent配置与记忆",
        "30_全局事实与决策",
        "40_跨Agent交接/会话认领",
        "50_检索通道",
        "60_模板",
        "70_原始材料收件箱",
        "80_敏感隔离_不要放进来",
        "90_归档",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "00_入口/06_Agent会话加载卡.md").write_text("# Session card\n", encoding="utf-8")

    project = root / "10_项目工作区" / "示例应用"
    for rel in (
        "10_当前任务",
        "20_交接记录",
        "30_开发文档",
        "40_验证记录",
        "50_事实与决策",
        "60_会话摘要",
        "90_原始材料索引",
    ):
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / "00_项目总览.md").write_text("# 示例应用\n\nOverview\n", encoding="utf-8")
    (project / "10_当前任务/00_任务索引.md").write_text("# 当前任务\n\nCurrent task\n", encoding="utf-8")
    (project / "20_交接记录/2026-08-25_交接.md").write_text(
        "---\nmemory_type: handoff\nrecord_type: handoff\ntitle: 最新交接\nstate: active\n---\n# 最新交接\n\nHandoff\n",
        encoding="utf-8",
    )
    (project / "40_验证记录/2026-08-25_验证.md").write_text(
        "---\nmemory_type: validation\nrecord_type: validation\ntitle: 最新验证\nstate: active\n---\n# 最新验证\n\nValidation\n",
        encoding="utf-8",
    )
    return root


class LayoutAdapterTests(unittest.TestCase):
    def test_chinese_fixture_is_supported_by_all_read_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_zh_vault(Path(td))
            layout = detect_layout(vault)
            self.assertEqual(layout.layout_id, "agent-brain-zh-v1")
            self.assertEqual(list_projects(vault), ["示例应用"])

            records = scan_records(vault)
            by_path = {item["path"]: item for item in records}
            self.assertEqual(by_path["10_项目工作区/示例应用/10_当前任务/00_任务索引.md"]["record_type"], "task")
            self.assertEqual(by_path["10_项目工作区/示例应用/20_交接记录/2026-08-25_交接.md"]["record_type"], "handoff")
            self.assertEqual(by_path["10_项目工作区/示例应用/40_验证记录/2026-08-25_验证.md"]["record_type"], "validation")

            pack = build_context(vault, project="示例应用", max_tokens=8000)
            self.assertGreater(pack["section_count"], 0)
            sources = {item["source_path"] for item in pack["sections"]}
            self.assertIn("10_项目工作区/示例应用/00_项目总览.md", sources)
            self.assertTrue(any(path.startswith("10_项目工作区/示例应用/10_当前任务/") for path in sources))
            self.assertTrue(any(path.startswith("10_项目工作区/示例应用/20_交接记录/") for path in sources))
            self.assertTrue(any(path.startswith("10_项目工作区/示例应用/40_验证记录/") for path in sources))

    def test_migrated_chinese_vault_ignores_auxiliary_english_markers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_zh_vault(Path(td))
            (vault / "AGENTS.md").write_text("# host policy\n", encoding="utf-8")
            (vault / ".agent-brain").mkdir()
            (vault / ".agent-brain/manifest.json").write_text(
                '{"vault_format_version": 1}\n', encoding="utf-8"
            )
            (vault / "50_retrieval/indexes").mkdir(parents=True)
            self.assertEqual(detect_layout(vault).layout_id, "agent-brain-zh-v1")

    def test_conflicting_core_markers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "10_projects").mkdir()
            (root / "10_项目工作区").mkdir()
            with self.assertRaises(LayoutDetectionError):
                detect_layout(root)

    def test_chinese_write_callers_use_selected_slots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = make_zh_vault(Path(td))
            added = add_project(vault, "新增项目")
            self.assertTrue((added / "00_项目总览.md").is_file())
            self.assertTrue((added / "10_当前任务/00_任务索引.md").is_file())

            packet = session_start(vault, project="示例应用", include_context=False)
            self.assertEqual(
                packet["paths"]["current_work"],
                "10_项目工作区/示例应用/10_当前任务/00_任务索引.md",
            )

            claim = acquire_claim(
                vault,
                session_id="zh-session",
                task="Chinese layout write path",
                planned_paths=["10_项目工作区/示例应用/10_当前任务/new.md"],
                filename="zh-claim.md",
            )
            self.assertIn("40_跨Agent交接/会话认领", str(claim))

            promoted = promote_memory(
                vault,
                project="示例应用",
                title="中文布局决策",
                conclusion="保留统一适配器",
                source="fixture",
                filename="zh-decision.md",
            )
            self.assertEqual(
                promoted["path"],
                "10_项目工作区/示例应用/50_事实与决策/zh-decision.md",
            )
            self.assertEqual(list_review_due(vault, project="示例应用")["project"], "示例应用")


if __name__ == "__main__":
    unittest.main()
