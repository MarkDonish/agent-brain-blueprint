from __future__ import annotations

import json
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
