from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
DEMO = ROOT / "examples" / "demo-vault"


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(SRC))
        sys.path.insert(0, str(SCRIPTS))
        from agent_brain.mcp.server import McpServer

        self.server = McpServer(DEMO)

    def test_initialize_and_tools_list(self) -> None:
        init_res = self.server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertIsNotNone(init_res)
        self.assertEqual(init_res["id"], 1)
        self.assertEqual(init_res["result"]["serverInfo"]["name"], "agent-brain")

        tools_res = self.server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertIsNotNone(tools_res)
        tools = tools_res["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        self.assertIn("agent_brain_doctor", tool_names)
        self.assertIn("agent_brain_search", tool_names)
        self.assertIn("agent_brain_context", tool_names)
        self.assertIn("agent_brain_claim_status", tool_names)
        self.assertIn("agent_brain_claim_gate", tool_names)
        self.assertIn("agent_brain_claim_acquire", tool_names)
        self.assertIn("agent_brain_claim_close", tool_names)
        self.assertIn("agent_brain_promote_memory", tool_names)
        self.assertIn("agent_brain_retrieve_status", tool_names)
        self.assertIn("agent_brain_retrieve_check", tool_names)
        self.assertIn("agent_brain_retrieve_refresh", tool_names)
        self.assertIn("agent_brain_graph_query", tool_names)

    def test_retrieval_generation_and_graph_tools(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            shutil.copytree(DEMO, vault)
            server = type(self.server)(vault)

            refresh = server.dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "agent_brain_retrieve_refresh",
                        "arguments": {"vault_path": str(vault)},
                    },
                }
            )
            self.assertFalse(refresh["result"].get("isError", False), refresh)
            refreshed = json.loads(refresh["result"]["content"][0]["text"])
            self.assertTrue(refreshed["published"])
            generation_id = refreshed["generation_id"]

            for tool in ("agent_brain_retrieve_status", "agent_brain_retrieve_check"):
                response = server.dispatch(
                    {
                        "jsonrpc": "2.0",
                        "id": 11,
                        "method": "tools/call",
                        "params": {"name": tool, "arguments": {"vault_path": str(vault)}},
                    }
                )
                self.assertFalse(response["result"].get("isError", False), response)
                payload = json.loads(response["result"]["content"][0]["text"])
                self.assertEqual(payload["generation_id"], generation_id)

            graph = server.dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 12,
                    "method": "tools/call",
                    "params": {
                        "name": "agent_brain_graph_query",
                        "arguments": {
                            "vault_path": str(vault),
                            "project": "demo-notes-app",
                            "limit": 5,
                        },
                    },
                }
            )
            self.assertFalse(graph["result"].get("isError", False), graph)
            graph_payload = json.loads(graph["result"]["content"][0]["text"])
            self.assertEqual(graph_payload["generation_id"], generation_id)
            self.assertTrue(graph_payload["nodes"])

    def test_call_doctor_tool(self) -> None:
        call_res = self.server.dispatch({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "agent_brain_doctor", "arguments": {"vault_path": str(DEMO)}},
        })
        self.assertIsNotNone(call_res)
        content = call_res["result"]["content"]
        self.assertGreaterEqual(len(content), 1)
        text = content[0]["text"]
        self.assertIn("check_vault_format.py", text)

    def test_call_handoff_create_tool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            (vault / "10_projects" / "mcp-demo").mkdir(parents=True)
            call_res = self.server.dispatch({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "agent_brain_handoff_create",
                    "arguments": {
                        "vault_path": str(vault),
                        "project": "mcp-demo",
                        "summary": "Completed MCP handoff integration test.",
                        "completed_tasks": ["Added MCP handoff endpoint"],
                        "evidence": [{"command": "make test", "result": "PASS"}],
                        "active_decisions": ["Standardized intelligent handoff"],
                        "next_steps": ["Ship v0.9.1"],
                    },
                },
            })
            self.assertIsNotNone(call_res)
            content = call_res["result"]["content"]
            data = json.loads(content[0]["text"])
            self.assertTrue(data["ok"])
            self.assertTrue((vault / data["path"]).is_file())

    def test_call_context_tool(self) -> None:
        call_res = self.server.dispatch({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "agent_brain_context",
                "arguments": {
                    "vault_path": str(DEMO),
                    "project": "demo-notes-app",
                    "task": "test mcp context",
                },
            },
        })
        self.assertIsNotNone(call_res)
        content = call_res["result"]["content"]
        text = content[0]["text"]
        self.assertIn("# Context pack", text)


if __name__ == "__main__":
    unittest.main()
