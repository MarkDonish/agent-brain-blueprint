"""Zero-dependency stdio Model Context Protocol (MCP) server for agent-brain."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

from agent_brain import __version__
from agent_brain.cli.claim_ops import acquire_claim, close_claim
from agent_brain.cli.runner import run_script_capture
from agent_brain.context.builder import build_context
from agent_brain.handoff.engine import create_handoff
from agent_brain.memory.promote import promote_memory
from agent_brain.paths import ensure_scripts_on_path
from agent_brain.retrieval.index import rebuild_index
from agent_brain.retrieval.query import search

PROTOCOL_VERSION = "2024-11-05"

TOOL_DEFINITIONS = [
    {
        "name": "agent_brain_doctor",
        "description": "Run health, format, governance, and session claim doctor checks on an Agent-Brain vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault directory (defaults to configured vault).",
                },
                "strict": {
                    "type": "boolean",
                    "description": "Enable strict validation checks.",
                },
                "project": {
                    "type": "string",
                    "description": "Filter checks by project slug.",
                },
            },
        },
    },
    {
        "name": "agent_brain_search",
        "description": "Search vault memories, decisions, handoffs, and tasks using derived SQLite FTS5 index. Results are candidates only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text or phrase search query (supports Chinese and English).",
                },
                "project": {
                    "type": "string",
                    "description": "Filter results to a specific project slug.",
                },
                "record_type": {
                    "type": "string",
                    "description": "Filter by record type (decision, task, validation, handoff, summary, memory).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of search results (default 10, max 50).",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "agent_brain_context",
        "description": "Build a compact, token-budgeted context pack (overview, current work, active decisions, summaries) for an agent task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project slug under 10_projects/.",
                },
                "task": {
                    "type": "string",
                    "description": "Current task description.",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum token budget (default 4000).",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["project", "task"],
        },
    },
    {
        "name": "agent_brain_claim_status",
        "description": "List all active, pending, and expired session claims in the vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
        },
    },
    {
        "name": "agent_brain_claim_gate",
        "description": "Check whether planned file paths conflict with other active session claims before writing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "planned_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of vault-relative file paths the session plans to write to.",
                },
                "session_id": {
                    "type": "string",
                    "description": "The current session ID (used to exclude self-conflicts).",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["planned_paths"],
        },
    },
    {
        "name": "agent_brain_claim_acquire",
        "description": "Acquire a new narrow session claim file before modifying shared memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier.",
                },
                "task": {
                    "type": "string",
                    "description": "Task description for the claim.",
                },
                "planned_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Vault-relative paths to claim.",
                },
                "claimed_by": {
                    "type": "string",
                    "description": "Name of the agent host acquiring the claim (e.g. antigravity, claude, codex).",
                },
                "hours": {
                    "type": "integer",
                    "description": "Claim duration in hours (default 8).",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["session_id", "task", "planned_paths"],
        },
    },
    {
        "name": "agent_brain_claim_close",
        "description": "Mark an active session claim closed with a completion summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_path": {
                    "type": "string",
                    "description": "Vault-relative or absolute path to the claim file.",
                },
                "summary": {
                    "type": "string",
                    "description": "Closeout completion summary.",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["claim_path"],
        },
    },
    {
        "name": "agent_brain_promote_memory",
        "description": "Explicitly promote a verified durable decision or fact to the vault. Never call automatically from ungrounded chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project slug under 10_projects/.",
                },
                "title": {
                    "type": "string",
                    "description": "Clear, descriptive title.",
                },
                "conclusion": {
                    "type": "string",
                    "description": "Concrete decision or durable fact statement.",
                },
                "source": {
                    "type": "string",
                    "description": "Provenance source path, URL, or decision reference.",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["tentative", "observed", "verified"],
                    "description": "Confidence level (production risk requires verified).",
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["decision", "fact", "lesson", "workflow", "evidence"],
                    "description": "Type of memory record (default decision).",
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "agent", "global"],
                    "description": "Scope of the memory record.",
                },
                "risk_boundary": {
                    "type": "string",
                    "enum": ["normal", "security", "production", "agent-configuration", "privacy"],
                    "description": "Risk boundary level.",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["project", "title", "conclusion", "source", "confidence"],
        },
    },
    {
        "name": "agent_brain_handoff_create",
        "description": "Create a structured, source-backed session handoff card with audit trail, active/superseded decisions, next steps, and automatic claim closeout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name or slug under 10_projects/ or 10_项目工作区/.",
                },
                "summary": {
                    "type": "string",
                    "description": "1-3 sentence 30-second status and summary of work done.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session identifier (e.g. 20260815-antigravity).",
                },
                "completed_tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of completed tasks / features.",
                },
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "result": {"type": "string"},
                        },
                        "required": ["command", "result"],
                    },
                    "description": "Fresh validation evidence (verification commands and results).",
                },
                "active_decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Active architectural decisions established or re-confirmed.",
                },
                "superseded_decisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "decision": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["decision", "reason"],
                    },
                    "description": "Superseded / obsoleted decisions with reason.",
                },
                "next_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Prioritized actionable next steps (P0, P1, P2...).",
                },
                "blockers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known risks, blockers, or upstream issues.",
                },
                "claim_path": {
                    "type": "string",
                    "description": "Specific claim file to close.",
                },
                "close_claim": {
                    "type": "boolean",
                    "description": "Auto-close matching claim or specified claim (default true).",
                },
                "owner": {
                    "type": "string",
                    "description": "Author or agent name.",
                },
                "to_agent": {
                    "type": "string",
                    "description": "Next receiver / agent (default next-session).",
                },
                "vault_path": {
                    "type": "string",
                    "description": "Path to the agent-brain vault.",
                },
            },
            "required": ["project", "summary"],
        },
    },
]


class McpServer:
    def __init__(self, default_vault: Path | None = None) -> None:
        self.default_vault = default_vault.expanduser().resolve() if default_vault else Path.cwd()

    def resolve_vault(self, custom_path: str | None) -> Path:
        if custom_path and str(custom_path).strip():
            p = Path(custom_path).expanduser().resolve()
            if p.is_dir():
                return p
        return self.default_vault

    def handle_call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        vault = self.resolve_vault(args.get("vault_path"))
        if not vault.is_dir():
            return {
                "content": [{"type": "text", "text": f"Error: vault directory not found: {vault}"}],
                "isError": True,
            }

        try:
            if name == "agent_brain_doctor":
                argv = [str(vault), "--json"]
                if args.get("strict"):
                    argv.append("--strict")
                if args.get("project"):
                    argv.extend(["--project", str(args["project"])])
                code, stdout, stderr = run_script_capture("doctor", argv)
                text = stdout if stdout.strip() else (stderr or f"doctor exited with code {code}")
                return {"content": [{"type": "text", "text": text}], "isError": code != 0}

            elif name == "agent_brain_search":
                query = str(args.get("query", "")).strip()
                if not query:
                    return {"content": [{"type": "text", "text": "Error: query parameter is required"}], "isError": True}
                project = args.get("project")
                record_type = args.get("record_type")
                limit = int(args.get("limit", 10))
                # Ensure index exists
                index_file = vault / "50_retrieval" / "indexes" / "fts.sqlite"
                if not index_file.is_file():
                    rebuild_index(vault)
                res = search(vault, query, project=project, record_type=record_type, limit=limit)
                return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]}

            elif name == "agent_brain_context":
                project = str(args.get("project", "")).strip()
                task = str(args.get("task", "")).strip()
                max_tokens = int(args.get("max_tokens", 4000))
                pack = build_context(vault, project=project, task=task, max_tokens=max_tokens)
                return {"content": [{"type": "text", "text": str(pack.get("document", ""))}]}

            elif name == "agent_brain_claim_status":
                argv = [str(vault)]
                code, stdout, stderr = run_script_capture("check_session_claims", argv)
                text = stdout if stdout.strip() else stderr
                return {"content": [{"type": "text", "text": text}], "isError": code != 0}

            elif name == "agent_brain_claim_gate":
                paths = args.get("planned_paths", [])
                if not isinstance(paths, list) or not paths:
                    return {"content": [{"type": "text", "text": "Error: planned_paths must be a non-empty list"}], "isError": True}
                argv = [str(vault)]
                for p in paths:
                    argv.extend(["--path", str(p)])
                if args.get("session_id"):
                    argv.extend(["--session-id", str(args["session_id"])])
                code, stdout, stderr = run_script_capture("check_claim_gate", argv)
                text = stdout if stdout.strip() else stderr
                return {"content": [{"type": "text", "text": text}], "isError": code != 0}

            elif name == "agent_brain_claim_acquire":
                sid = str(args.get("session_id", "")).strip()
                task = str(args.get("task", "")).strip()
                paths = [str(p) for p in args.get("planned_paths", [])]
                claimed_by = str(args.get("claimed_by", "mcp-agent"))
                hours = int(args.get("hours", 8))
                created = acquire_claim(vault, session_id=sid, task=task, planned_paths=paths, claimed_by=claimed_by, hours=hours)
                rel_path = str(created.relative_to(vault))
                return {"content": [{"type": "text", "text": json.dumps({"status": "created", "claim_path": rel_path, "session_id": sid}, indent=2)}]}

            elif name == "agent_brain_claim_close":
                cpath = str(args.get("claim_path", "")).strip()
                summary = str(args.get("summary", "Closed via MCP agent_brain_claim_close"))
                closed = close_claim(vault, cpath, summary=summary)
                rel_path = str(closed.relative_to(vault))
                return {"content": [{"type": "text", "text": json.dumps({"status": "closed", "claim_path": rel_path}, indent=2)}]}

            elif name == "agent_brain_promote_memory":
                project = str(args.get("project", "")).strip()
                title = str(args.get("title", "")).strip()
                conclusion = str(args.get("conclusion", "")).strip()
                source = str(args.get("source", "")).strip()
                confidence = str(args.get("confidence", "verified")).strip()
                memory_type = str(args.get("memory_type", "decision")).strip()
                scope = str(args.get("scope", "project")).strip()
                risk = str(args.get("risk_boundary", "normal")).strip()
                report = promote_memory(
                    vault,
                    project=project,
                    title=title,
                    conclusion=conclusion,
                    source=source,
                    confidence=confidence,
                    memory_type=memory_type,
                    scope=scope,
                    risk_boundary=risk,
                )
                return {"content": [{"type": "text", "text": json.dumps(report, ensure_ascii=False, indent=2)}]}

            elif name in ("agent_brain_handoff_create", "agent_brain_session_end"):
                project = str(args.get("project", "")).strip()
                summary = str(args.get("summary", "")).strip()
                session_id = args.get("session_id")
                completed_tasks = args.get("completed_tasks")
                evidence = args.get("evidence")
                active_decisions = args.get("active_decisions")
                superseded_decisions = args.get("superseded_decisions")
                next_steps = args.get("next_steps")
                blockers = args.get("blockers")
                claim = args.get("claim_path")
                close_claim_file = bool(args.get("close_claim", True))
                owner = str(args.get("owner", "mcp-agent"))
                to_agent = str(args.get("to_agent", "next-session"))
                res = create_handoff(
                    vault,
                    project=project,
                    summary=summary,
                    session_id=session_id,
                    completed_tasks=completed_tasks,
                    evidence=evidence,
                    active_decisions=active_decisions,
                    superseded_decisions=superseded_decisions,
                    next_steps=next_steps,
                    blockers=blockers,
                    claim=claim,
                    close_claim_file=close_claim_file,
                    owner=owner,
                    to_agent=to_agent,
                )
                return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]}

            else:
                return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}

        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Error executing {name}: {type(exc).__name__}: {exc}"}], "isError": True}

    def dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "agent-brain", "version": __version__},
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOL_DEFINITIONS}}

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}
            res = self.handle_call_tool(tool_name, tool_args)
            return {"jsonrpc": "2.0", "id": msg_id, "result": res}

        else:
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            return None


def run_mcp_server(default_vault: Path | None = None) -> int:
    """Run MCP server over stdio."""
    ensure_scripts_on_path()
    server = McpServer(default_vault)
    reader = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    writer = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

    while True:
        try:
            line = reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            # Handle Content-Length header framing if present
            if line.lower().startswith("content-length:"):
                length_part = line.split(":", 1)[1].strip()
                length = int(length_part)
                # consume empty separator line (framing requires reading it)
                reader.readline()
                body = reader.read(length)
                message = json.loads(body)
            else:
                message = json.loads(line)

            response = server.dispatch(message)
            if response is not None:
                out_str = json.dumps(response, ensure_ascii=False)
                writer.write(out_str + "\n")
                writer.flush()

        except (BrokenPipeError, KeyboardInterrupt):
            break
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse or dispatch error: {exc}"},
            }
            try:
                writer.write(json.dumps(err_resp) + "\n")
                writer.flush()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    vault_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(run_mcp_server(vault_arg))
