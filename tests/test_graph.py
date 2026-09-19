from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from agent_brain.retrieval.graph import query_graph  # noqa: E402
from agent_brain.retrieval.index import default_index_path, rebuild_index  # noqa: E402


class GraphTests(unittest.TestCase):
    def test_explicit_relations_and_unresolved_are_evidenced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            (vault / "00_entrypoint").mkdir(parents=True)
            decisions = vault / "10_projects" / "app" / "50_decisions"
            validations = vault / "10_projects" / "app" / "40_validation"
            decisions.mkdir(parents=True)
            validations.mkdir(parents=True)
            (vault / "00_entrypoint" / "SESSION_START_CARD.md").write_text("# Card", encoding="utf-8")
            (vault / "AGENTS.md").write_text("# Rules", encoding="utf-8")
            (vault / "10_projects" / "app" / "PROJECT_OVERVIEW.md").write_text("# App", encoding="utf-8")
            (decisions / "old.md").write_text("---\nrecord_id: old\nmemory_type: decision\n---\n# Old\n", encoding="utf-8")
            (decisions / "new.md").write_text("---\nrecord_id: new\nmemory_type: decision\nsupersedes: old\nderived_from: missing.md\n---\n# New\nSimilar prose does not create edges.\n", encoding="utf-8")
            (validations / "check.md").write_text("---\nrecord_id: check\nmemory_type: validation\nvalidates: 10_projects/app/50_decisions/new.md\n---\n# Check\nSimilar prose does not create edges.\n", encoding="utf-8")
            report = rebuild_index(vault)
            index = default_index_path(vault)
            supersedes = query_graph(index, relation_type="SUPERSEDES", generation_id=report["generation_id"])
            self.assertEqual(len(supersedes["relations"]), 1)
            self.assertEqual(supersedes["relations"][0]["target_node"], "record:old")
            validates = query_graph(index, relation_type="VALIDATES", generation_id=report["generation_id"])
            self.assertEqual(validates["relations"][0]["target_node"], "record:new")
            unresolved = query_graph(index, relation_type="DERIVED_FROM", generation_id=report["generation_id"])
            self.assertEqual(unresolved["relations"][0]["target_node"], None)
            self.assertEqual(unresolved["relations"][0]["unresolved_ref"], "missing.md")

    def test_directory_edges_and_stable_graph_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            (vault / "00_entrypoint").mkdir(parents=True)
            (vault / "10_projects" / "app" / "20_handoffs").mkdir(parents=True)
            (vault / "10_projects" / "second").mkdir(parents=True)
            (vault / "00_entrypoint" / "SESSION_START_CARD.md").write_text("# Card", encoding="utf-8")
            (vault / "10_projects" / "app" / "PROJECT_OVERVIEW.md").write_text("# App", encoding="utf-8")
            (vault / "10_projects" / "app" / "20_handoffs" / "h.md").write_text("---\nrecord_id: h\nmemory_type: handoff\n---\n# Handoff\n", encoding="utf-8")
            report = rebuild_index(vault)
            result = query_graph(default_index_path(vault), relation_type="HANDOFF_FOR", limit=1, generation_id=report["generation_id"])
            self.assertEqual(result["relations"][0]["relation_type"], "HANDOFF_FOR")
            projects = query_graph(default_index_path(vault), node_type="Project", limit=1, generation_id=report["generation_id"])
            self.assertTrue(projects["has_more"])
            next_page = query_graph(default_index_path(vault), node_type="Project", limit=1, cursor=projects["next_cursor"], generation_id=report["generation_id"])
            self.assertNotEqual(projects["nodes"][0]["node_id"], next_page["nodes"][0]["node_id"])


if __name__ == "__main__":
    unittest.main()
