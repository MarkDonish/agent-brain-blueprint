"""Deterministic, evidence-bearing relations for the derived index.

The graph is intentionally small.  It only creates edges from directory
membership or explicit frontmatter references; prose similarity is never
treated as a relationship.  Markdown remains the source of truth and each
row keeps the path needed to reopen that source.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any

from agent_brain.retrieval.cursor import CursorError, decode_cursor, encode_cursor

NODE_TYPES = {"Project", "Task", "Decision", "Handoff", "Validation", "Source", "Memory"}
RELATION_TYPES = {"BELONGS_TO", "HANDOFF_FOR", "VALIDATES", "SUPERSEDES", "DERIVED_FROM", "NEXT_STEP"}

_RECORD_TO_NODE = {
    "task": "Task",
    "decision": "Decision",
    "handoff": "Handoff",
    "validation": "Validation",
    "source": "Source",
    "claim": "Handoff",
    "summary": "Memory",
    "memory": "Memory",
}
_EXPLICIT_FIELDS = {
    "validates": "VALIDATES",
    "validate": "VALIDATES",
    "validation_for": "VALIDATES",
    "validates_record_id": "VALIDATES",
    "supersedes": "SUPERSEDES",
    "supersedes_record_id": "SUPERSEDES",
    "derived_from": "DERIVED_FROM",
    "derived_from_record_id": "DERIVED_FROM",
    "next_step": "NEXT_STEP",
    "next_steps": "NEXT_STEP",
    "next_step_record_id": "NEXT_STEP",
}


def create_graph_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS nodes (
          node_id TEXT PRIMARY KEY,
          node_type TEXT NOT NULL,
          record_id TEXT,
          path TEXT,
          project TEXT,
          title TEXT NOT NULL,
          source_path TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project);
        CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
        CREATE TABLE IF NOT EXISTS relations (
          relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_node TEXT NOT NULL,
          target_node TEXT,
          relation_type TEXT NOT NULL,
          evidence TEXT NOT NULL,
          source_path TEXT NOT NULL,
          confidence TEXT NOT NULL,
          unresolved_ref TEXT,
          UNIQUE(source_node, target_node, relation_type, unresolved_ref)
        );
        CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
        CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_node);
        CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_node);
        """
    )


def _node_type(record: Mapping[str, Any]) -> str:
    return _RECORD_TO_NODE.get(str(record.get("record_type") or "memory"), "Memory")


def _as_refs(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _clean_ref(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("record_id", "path", "source_path", "id", "target"):
            if value.get(key):
                return str(value[key]).strip()
        return ""
    return str(value).strip()


def _resolve_target(ref: str, by_record: Mapping[str, str], by_path: Mapping[str, str]) -> tuple[str | None, str | None]:
    if not ref:
        return None, None
    if ref in by_record:
        return by_record[ref], None
    if ref in by_path:
        return by_path[ref], None
    normalized = ref.replace("\\", "/").lstrip("./")
    if normalized in by_path:
        return by_path[normalized], None
    # Explicit ``record:...`` and ``project:...`` identifiers are accepted as
    # identifiers only when the corresponding node exists.  Do not create a
    # guessed node for a typo; preserve it as an unresolved reference.
    if normalized.startswith("record:") and normalized[7:] in by_record:
        return by_record[normalized[7:]], None
    if normalized.startswith("project:"):
        candidate = normalized[8:]
        node = f"project:{candidate}"
        if node in by_record:
            return node, None
    return None, ref


def build_graph(
    conn: sqlite3.Connection,
    records: Iterable[Mapping[str, Any]],
    *,
    projects: Iterable[str] = (),
) -> dict[str, int]:
    """Populate graph tables and return deterministic node/relation counts."""

    create_graph_schema(conn)
    rows = [dict(record) for record in records]
    project_names = {str(project) for project in projects if str(project)}
    project_names.update(str(row.get("project") or "") for row in rows if row.get("project"))

    # Project IDs also live in ``by_record`` so explicit project references can
    # resolve without a separate lookup table.
    by_record: dict[str, str] = {}
    by_path: dict[str, str] = {}
    for project in sorted(project_names):
        node_id = f"project:{project}"
        by_record[node_id] = node_id
        conn.execute(
            "INSERT OR REPLACE INTO nodes(node_id,node_type,record_id,path,project,title,source_path,metadata_json) VALUES (?,?,?,?,?,?,?,?)",
            (node_id, "Project", node_id, project, project, project, project, "{}"),
        )

    for row in rows:
        record_id = str(row.get("record_id") or "")
        path = str(row.get("path") or row.get("source_path") or "").replace("\\", "/")
        node_id = f"record:{record_id or path}"
        by_record[record_id] = node_id
        by_record[node_id] = node_id
        by_path[path] = node_id
        metadata = row.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        conn.execute(
            "INSERT OR REPLACE INTO nodes(node_id,node_type,record_id,path,project,title,source_path,metadata_json) VALUES (?,?,?,?,?,?,?,?)",
            (
                node_id,
                _node_type(row),
                record_id,
                path,
                str(row.get("project") or ""),
                str(row.get("title") or path),
                path,
                json.dumps(dict(metadata), ensure_ascii=False, sort_keys=True, default=str),
            ),
        )

    # Prefer a canonical project overview as the reopen target for Project
    # nodes. If a fixture has no overview, retain the project directory path as
    # a transparent pointer rather than inventing a Markdown record.
    for project in sorted(project_names):
        overview = next(
            (
                str(row.get("path") or "").replace("\\", "/")
                for row in rows
                if str(row.get("project") or "") == project
                and str(row.get("record_type") or "") == "summary"
                and str(row.get("path") or "").rsplit("/", 1)[-1] in {"PROJECT_OVERVIEW.md", "00_项目总览.md"}
            ),
            None,
        )
        if overview:
            conn.execute(
                "UPDATE nodes SET path=?, source_path=? WHERE node_id=?",
                (overview, overview, f"project:{project}"),
            )

    # Directory-derived edges are high-confidence, but still carry evidence.
    for row in rows:
        record_id = str(row.get("record_id") or "")
        source = by_record.get(record_id)
        project = str(row.get("project") or "")
        path = str(row.get("path") or row.get("source_path") or "").replace("\\", "/")
        if not source or not project:
            continue
        project_node = f"project:{project}"
        conn.execute(
            "INSERT OR IGNORE INTO relations(source_node,target_node,relation_type,evidence,source_path,confidence,unresolved_ref) VALUES (?,?,?,?,?,?,?)",
            (source, project_node, "BELONGS_TO", "layout project directory", path, "deterministic", None),
        )
        if _node_type(row) == "Handoff":
            conn.execute(
                "INSERT OR IGNORE INTO relations(source_node,target_node,relation_type,evidence,source_path,confidence,unresolved_ref) VALUES (?,?,?,?,?,?,?)",
                (source, project_node, "HANDOFF_FOR", "layout project directory", path, "deterministic", None),
            )

    for row in rows:
        record_id = str(row.get("record_id") or "")
        source = by_record.get(record_id)
        path = str(row.get("path") or row.get("source_path") or "").replace("\\", "/")
        metadata = row.get("metadata")
        if not source or not isinstance(metadata, Mapping):
            continue
        for field, relation_type in _EXPLICIT_FIELDS.items():
            if field not in metadata:
                continue
            for raw_ref in _as_refs(metadata.get(field)):
                ref = _clean_ref(raw_ref)
                if not ref:
                    continue
                # Relation fields may also be used for human prose (for
                # example ``next_step: Run the test suite``). Only path-like,
                # known record IDs, or compact explicit identifiers become
                # edges; prose similarity is never promoted to a relation.
                if any(char.isspace() for char in ref) and ref not in by_record and ref not in by_path:
                    continue
                target, unresolved = _resolve_target(ref, by_record, by_path)
                evidence = f"frontmatter:{field}={ref}"
                conn.execute(
                    "INSERT OR IGNORE INTO relations(source_node,target_node,relation_type,evidence,source_path,confidence,unresolved_ref) VALUES (?,?,?,?,?,?,?)",
                    (source, target, relation_type, evidence, path, "high", unresolved),
                )

    conn.commit()
    node_count = int(conn.execute("SELECT count(*) FROM nodes").fetchone()[0])
    relation_count = int(conn.execute("SELECT count(*) FROM relations").fetchone()[0])
    unresolved_count = int(conn.execute("SELECT count(*) FROM relations WHERE unresolved_ref IS NOT NULL").fetchone()[0])
    return {"node_count": node_count, "relation_count": relation_count, "unresolved_count": unresolved_count}


def relation_summary(conn: sqlite3.Connection, node_id: str, *, max_items: int = 8) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT relation_type,target_node,unresolved_ref,confidence FROM relations WHERE source_node=? OR target_node=? ORDER BY relation_type, target_node, unresolved_ref LIMIT ?",
        (node_id, node_id, max(1, int(max_items))),
    ).fetchall()
    return [
        {
            "relation_type": row[0],
            "target_node": row[1],
            "unresolved_ref": row[2],
            "confidence": row[3],
        }
        for row in rows
    ]


def query_graph(
    index_path,
    *,
    project: str | None = None,
    node_type: str | None = None,
    relation_type: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
    generation_id: str = "legacy",
) -> dict[str, Any]:
    """Query graph nodes or relations using deterministic cursor pagination."""

    if node_type:
        node_type = str(node_type).strip().capitalize()
    if relation_type:
        relation_type = str(relation_type).strip().upper()
    conn = sqlite3.connect(str(index_path))
    conn.row_factory = sqlite3.Row
    try:
        try:
            offset = decode_cursor(cursor, generation_id, kind="graph") if cursor else 0
        except CursorError as exc:
            return {"ok": False, "error": str(exc), "nodes": [], "relations": []}
        lim = max(1, min(int(limit), 200))
        if relation_type:
            clauses = ["r.relation_type = ?"]
            params: list[Any] = [relation_type]
            if project:
                clauses.append("(sn.project = ? OR tn.project = ?)")
                params.extend([project, project])
            sql = f"""
                SELECT r.relation_id,r.source_node,r.target_node,r.relation_type,r.evidence,
                       r.source_path,r.confidence,r.unresolved_ref,
                       sn.project AS source_project,tn.project AS target_project
                FROM relations r
                LEFT JOIN nodes sn ON sn.node_id=r.source_node
                LEFT JOIN nodes tn ON tn.node_id=r.target_node
                WHERE {' AND '.join(clauses)}
                ORDER BY r.relation_type,r.source_node,coalesce(r.target_node,''),coalesce(r.unresolved_ref,''),r.relation_id
            """
            all_rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            rows = all_rows[offset : offset + lim]
            result_key = "relations"
        else:
            clauses = ["1=1"]
            params = []
            if project:
                clauses.append("project = ?")
                params.append(project)
            if node_type:
                clauses.append("node_type = ?")
                params.append(node_type)
            sql = f"SELECT node_id,node_type,record_id,path,project,title,source_path FROM nodes WHERE {' AND '.join(clauses)} ORDER BY node_type,node_id"
            all_rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            rows = all_rows[offset : offset + lim]
            result_key = "nodes"
        has_more = offset + lim < len(all_rows)
        payload: dict[str, Any] = {
            "ok": True,
            "generation_id": generation_id,
            result_key: rows,
            "limit": lim,
            "has_more": has_more,
            "next_cursor": encode_cursor(generation_id, offset + lim, kind="graph") if has_more else None,
            "note": "Graph edges are derived evidence; reopen source_path Markdown before acting.",
        }
        if result_key == "nodes":
            for row in payload["nodes"]:
                row["reopen"] = row.get("source_path") or row.get("path")
                row["relation_summary"] = relation_summary(conn, str(row["node_id"]))
        return payload
    except sqlite3.OperationalError as exc:
        return {"ok": False, "error": str(exc), "nodes": [], "relations": []}
    finally:
        conn.close()


__all__ = [
    "NODE_TYPES",
    "RELATION_TYPES",
    "build_graph",
    "create_graph_schema",
    "graph_query",
    "query_graph",
    "relation_summary",
]

# Alias used by callers that name the operation after the CLI command.
graph_query = query_graph
