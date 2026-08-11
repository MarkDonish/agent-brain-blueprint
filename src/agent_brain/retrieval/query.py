"""Query the derived FTS index. Hits are candidates only — reopen Markdown."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from agent_brain.retrieval.index import default_index_path
from agent_brain.retrieval.scan import is_active_for_context

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9_./-]+")


def _fts_query(raw: str) -> str:
    """Build a simple FTS5 query from free text (AND of tokens)."""
    tokens = _SAFE_TOKEN.findall(raw)
    if not tokens:
        # fallback: quote whole string stripped of quotes
        cleaned = raw.replace('"', " ").strip()
        return f'"{cleaned}"' if cleaned else '""'
    return " ".join(tokens)


def search(
    vault: Path,
    query: str,
    *,
    project: str | None = None,
    record_type: str | None = None,
    state: str | None = None,
    freshness: str | None = None,
    scope: str | None = None,
    risk_boundary: str | None = None,
    include_inactive: bool = False,
    limit: int = 20,
    index_path: Path | None = None,
) -> dict[str, Any]:
    vault = vault.expanduser().resolve()
    path = index_path or default_index_path(vault)
    if not path.is_file():
        return {
            "ok": False,
            "error": f"index missing: {path}; run: agent-brain retrieve rebuild {vault}",
            "hits": [],
            "hit_count": 0,
        }

    clauses = ["records_fts MATCH ?"]
    params: list[Any] = [_fts_query(query)]
    if project:
        clauses.append("project = ?")
        params.append(project)
    if record_type:
        clauses.append("record_type = ?")
        params.append(record_type)
    if state:
        clauses.append("state = ?")
        params.append(state)
    if freshness:
        clauses.append("freshness = ?")
        params.append(freshness)
    if scope:
        clauses.append("scope = ?")
        params.append(scope)
    if risk_boundary:
        clauses.append("risk_boundary = ?")
        params.append(risk_boundary)

    sql = f"""
        SELECT
          record_id, path, project, record_type, memory_type, title, body,
          state, freshness, scope, risk_boundary, updated_at,
          bm25(records_fts) AS score
        FROM records_fts
        WHERE {" AND ".join(clauses)}
        ORDER BY score
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 200)))

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        return {"ok": False, "error": str(exc), "hits": [], "hit_count": 0}
    finally:
        conn.close()

    hits: list[dict[str, Any]] = []
    for row in rows:
        item = {k: row[k] for k in row.keys()}
        if not include_inactive and not is_active_for_context(item):
            continue
        # Truncate body in result listing; reopen path for full truth
        body = str(item.get("body") or "")
        item["body_preview"] = body[:400]
        item.pop("body", None)
        item["candidate_only"] = True
        item["reopen"] = str(vault / str(item["path"]))
        hits.append(item)

    return {
        "ok": True,
        "derived": True,
        "canonical": "markdown",
        "index_path": str(path),
        "query": query,
        "fts_query": _fts_query(query),
        "filters": {
            "project": project,
            "record_type": record_type,
            "state": state,
            "freshness": freshness,
            "scope": scope,
            "risk_boundary": risk_boundary,
            "include_inactive": include_inactive,
        },
        "hit_count": len(hits),
        "hits": hits,
        "note": "Hits are retrieval candidates only. Reopen source Markdown before acting.",
    }
