"""Rebuild derived SQLite FTS5 index for a vault."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from agent_brain.retrieval.scan import scan_records

INDEX_REL = "50_retrieval/indexes/fts.sqlite"


def default_index_path(vault: Path) -> Path:
    return vault.expanduser().resolve() / INDEX_REL


def _normalize_cjk(text: str) -> str:
    """Insert spaces around CJK characters to enable fine-grained FTS5 indexing with unicode61."""
    if not text:
        return ""
    return re.sub(r"([\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af])", r" \1 ", text)


def rebuild_index(vault: Path, *, index_path: Path | None = None) -> dict[str, Any]:
    """Rebuild the FTS index from canonical Markdown. Safe to delete anytime."""
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"vault not found: {vault}")

    path = index_path or default_index_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    records = scan_records(vault)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE VIRTUAL TABLE records_fts USING fts5(
              title,
              body,
              raw_title UNINDEXED,
              raw_body UNINDEXED,
              path UNINDEXED,
              record_id UNINDEXED,
              project UNINDEXED,
              record_type UNINDEXED,
              memory_type UNINDEXED,
              state UNINDEXED,
              freshness UNINDEXED,
              scope UNINDEXED,
              risk_boundary UNINDEXED,
              updated_at UNINDEXED,
              tokenize = 'unicode61'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO meta(key, value) VALUES ('kind', 'agent-brain-fts'), ('version', '2')"
        )
        rows = [
            (
                _normalize_cjk(r["title"]),
                _normalize_cjk(r["body"]),
                r["title"],
                r["body"],
                r["path"],
                r["record_id"],
                r["project"],
                r["record_type"],
                r["memory_type"],
                r["state"],
                r["freshness"],
                r["scope"],
                r["risk_boundary"],
                r["updated_at"],
            )
            for r in records
        ]
        conn.executemany(
            """
            INSERT INTO records_fts(
              title, body, raw_title, raw_body, path, record_id, project, record_type, memory_type,
              state, freshness, scope, risk_boundary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "vault": str(vault),
        "index_path": str(path),
        "record_count": len(records),
        "derived": True,
        "rebuildable": True,
        "canonical": "markdown",
    }
