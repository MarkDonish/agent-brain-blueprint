from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
DEMO = ROOT / "examples" / "demo-vault"


def env_with_src() -> dict[str, str]:
    env = os.environ.copy()
    parts = [str(SRC), str(SCRIPTS)]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(parts + ([existing] if existing else []))
    return env


class RetrievalTests(unittest.TestCase):
    def test_rebuild_and_search_demo(self) -> None:
        sys.path.insert(0, str(SRC))
        sys.path.insert(0, str(SCRIPTS))
        from agent_brain.retrieval.index import default_index_path, rebuild_index
        from agent_brain.retrieval.query import search

        with tempfile.TemporaryDirectory() as directory:
            # copy demo lightly via rebuild on real demo path but write index to temp
            index = Path(directory) / "fts.sqlite"
            report = rebuild_index(DEMO, index_path=index)
            self.assertGreaterEqual(report["record_count"], 3)
            self.assertTrue(index.is_file())

            result = search(
                DEMO,
                "markdown canonical",
                project="demo-notes-app",
                index_path=index,
            )
            self.assertTrue(result["ok"], result)
            self.assertGreaterEqual(result["hit_count"], 1)
            paths = [h["path"] for h in result["hits"]]
            self.assertTrue(
                any("markdown-is-canonical" in p or "PROJECT_OVERVIEW" in p for p in paths),
                paths,
            )
            self.assertTrue(all(h.get("candidate_only") for h in result["hits"]))

    def test_excludes_expired_by_default(self) -> None:
        sys.path.insert(0, str(SRC))
        sys.path.insert(0, str(SCRIPTS))
        from agent_brain.retrieval.index import rebuild_index
        from agent_brain.retrieval.query import search

        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            # minimal vault files for scan
            (vault / "10_projects" / "app" / "50_decisions").mkdir(parents=True)
            (vault / "00_entrypoint").mkdir(parents=True)
            (vault / "00_entrypoint" / "SESSION_START_CARD.md").write_text("# start\n", encoding="utf-8")
            (vault / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            active = vault / "10_projects" / "app" / "50_decisions" / "active.md"
            active.write_text(
                """---
memory_type: decision
title: Keep rate limits
source: test
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2099-01-01
owner: demo
state: active
---
# Keep rate limits
rate limit password reset
""",
                encoding="utf-8",
            )
            expired = vault / "10_projects" / "app" / "50_decisions" / "old.md"
            expired.write_text(
                """---
memory_type: decision
title: Old expired fact
source: test
confidence: verified
freshness: expired
scope: project
risk_boundary: normal
next_review: 2020-01-01
owner: demo
state: expired
---
# Old expired fact
password reset unlimited
""",
                encoding="utf-8",
            )
            index = vault / "50_retrieval" / "indexes" / "fts.sqlite"
            rebuild_index(vault, index_path=index)
            result = search(vault, "password reset", project="app", index_path=index)
            self.assertTrue(result["ok"])
            titles = [h.get("title") for h in result["hits"]]
            self.assertIn("Keep rate limits", titles)
            self.assertNotIn("Old expired fact", titles)

    def test_cli_retrieve_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "v"
            init = subprocess.run(
                [sys.executable, "-m", "agent_brain", "init", "--destination", str(vault), "--project", "app"],
                cwd=str(ROOT),
                env=env_with_src(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            # add a decision so FTS has something task-related
            dec = vault / "10_projects" / "app" / "50_decisions" / "login.md"
            dec.write_text(
                """---
memory_type: decision
title: Login uses session cookies
source: test
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2099-01-01
owner: demo
state: active
---
# Login uses session cookies
""",
                encoding="utf-8",
            )
            rebuild = subprocess.run(
                [sys.executable, "-m", "agent_brain", "retrieve", "rebuild", str(vault)],
                cwd=str(ROOT),
                env=env_with_src(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebuild.returncode, 0, rebuild.stderr + rebuild.stdout)
            search = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_brain",
                    "retrieve",
                    "search",
                    str(vault),
                    "login cookies",
                    "--project",
                    "app",
                ],
                cwd=str(ROOT),
                env=env_with_src(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(search.returncode, 0, search.stderr + search.stdout)
            self.assertIn("candidate_only", search.stdout)

            ctx = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_brain",
                    "context",
                    "build",
                    str(vault),
                    "--project",
                    "app",
                    "--task",
                    "fix login",
                    "--max-tokens",
                    "4000",
                    "--json",
                    "--meta-only",
                ],
                cwd=str(ROOT),
                env=env_with_src(),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(ctx.returncode, 0, ctx.stderr + ctx.stdout)
            self.assertIn("estimated_tokens", ctx.stdout)
            self.assertIn("section_count", ctx.stdout)

    def test_cjk_multilingual_search(self) -> None:
        sys.path.insert(0, str(SRC))
        sys.path.insert(0, str(SCRIPTS))
        from agent_brain.retrieval.index import rebuild_index
        from agent_brain.retrieval.query import search

        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory) / "vault"
            (vault / "10_projects" / "ai-relay" / "50_decisions").mkdir(parents=True)
            (vault / "00_entrypoint").mkdir(parents=True)
            (vault / "00_entrypoint" / "SESSION_START_CARD.md").write_text("# start\n", encoding="utf-8")
            (vault / "AGENTS.md").write_text("# agents\n", encoding="utf-8")

            doc = vault / "10_projects" / "ai-relay" / "50_decisions" / "2026-08-11_relay.md"
            doc.write_text(
                """---
memory_type: decision
title: 中转部署与公网IP试运营决策
source: Mark 明确确认
confidence: verified
freshness: current
scope: project
risk_boundary: normal
next_review: 2099-01-01
owner: Mark
state: active
---
# 中转部署与公网IP试运营决策
生产机选型完成，采用公网IP直接试运营，暂缓购买域名。
""",
                encoding="utf-8",
            )
            rebuild_index(vault)

            for q in ["中转部署", "公网IP", "试运营", "生产机", "暂缓购买域名"]:
                res = search(vault, q, project="ai-relay")
                self.assertTrue(res["ok"], f"query {q} failed: {res}")
                self.assertGreaterEqual(res["hit_count"], 1, f"query {q} yielded 0 hits: {res}")
                self.assertEqual(res["hits"][0]["title"], "中转部署与公网IP试运营决策")


if __name__ == "__main__":
    unittest.main()
