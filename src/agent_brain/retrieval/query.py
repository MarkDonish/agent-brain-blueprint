"""Query the derived FTS index. Hits are candidates only — reopen Markdown."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from agent_brain.layout import detect_layout
from agent_brain.retrieval.cursor import CursorError, decode_cursor, encode_cursor
from agent_brain.retrieval.index import default_index_path, status_index
from agent_brain.retrieval.scan import is_active_for_context, source_inventory


def _fts_query(raw: str) -> str:
    """Build a robust FTS5 query supporting ASCII terms and CJK phrases."""

    tokens: list[str] = []
    for part in re.finditer(
        r"([A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*)|([\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+)", raw
    ):
        ascii_tok, cjk_tok = part.groups()
        if ascii_tok:
            clean = ascii_tok.strip("._/-")
            if clean:
                tokens.append(f'"{clean}"')
        elif cjk_tok:
            tokens.append(f'"{" ".join(list(cjk_tok))}"')
    if not tokens:
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]", " ", raw).strip()
        return f'"{cleaned}"' if cleaned else '""'
    return " AND ".join(tokens)


def _profile(detail: str | None = None, profile: str | None = None) -> str:
    value = str(detail or profile or "verify").strip().lower()
    aliases = {"compact": "scout", "default": "verify", "full": "auditor"}
    value = aliases.get(value, value)
    if value not in {"scout", "verify", "auditor"}:
        raise ValueError("detail/profile must be scout, verify, or auditor (compact/default/full aliases)")
    return value


def _path_rank(path: str, vault: Path) -> int:
    """Small deterministic boost for navigation pages.

    The boost is applied only after exact title matches. This keeps a precise
    record title ahead of an unrelated entrypoint while ensuring a navigation
    query does not get buried by a long report that repeats the same term.
    """

    normalized = path.replace("\\", "/")
    try:
        layout = detect_layout(vault)
    except Exception:
        layout = None
    if layout and normalized == layout.entrypoint_rel:
        return 3
    if normalized.endswith("/PROJECT_OVERVIEW.md") or normalized.endswith("/00_项目总览.md"):
        return 2
    if "/10_current_work/" in normalized or "/10_当前任务/" in normalized:
        return 1
    return 0


def _coverage_for_index(vault: Path, path: Path, generation_id: str, row_count: int) -> dict[str, Any]:
    try:
        current = default_index_path(vault)
    except Exception:
        current = path
    if path.resolve() == current.resolve() and generation_id != "legacy":
        try:
            result = status_index(vault)
            return {
                key: result.get(key)
                for key in (
                    "source_count",
                    "indexed_count",
                    "missing_source_count",
                    "stale_source_count",
                    "blocked_source_count",
                    "coverage_complete",
                )
            }
        except Exception:
            pass
    try:
        inventory = source_inventory(vault)
        return {
            "source_count": inventory["source_count"],
            "indexed_count": row_count,
            "missing_source_count": 0,
            "stale_source_count": 0,
            "blocked_source_count": inventory["blocked_source_count"],
            "coverage_complete": row_count == inventory["source_count"] and inventory["blocked_source_count"] == 0,
        }
    except Exception:
        return {
            "source_count": row_count,
            "indexed_count": row_count,
            "missing_source_count": 0,
            "stale_source_count": 0,
            "blocked_source_count": 0,
            "coverage_complete": True,
        }


def _relation_summary(conn: sqlite3.Connection, node_id: str) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(
            "SELECT relation_type,target_node,unresolved_ref,confidence FROM relations WHERE source_node=? OR target_node=? ORDER BY relation_type,target_node,unresolved_ref LIMIT 8",
            (f"record:{node_id}", f"record:{node_id}"),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {"relation_type": row[0], "target_node": row[1], "unresolved_ref": row[2], "confidence": row[3]}
        for row in rows
    ]


def _generation_meta(conn: sqlite3.Connection) -> tuple[str, dict[str, str]]:
    try:
        meta = dict(conn.execute("SELECT key,value FROM meta").fetchall())
    except sqlite3.Error:
        meta = {}
    return str(meta.get("generation_id") or "legacy"), meta


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
    detail: str | None = None,
    profile: str | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Search with pre-pagination active filtering and generation cursors."""

    vault = vault.expanduser().resolve()
    try:
        selected_profile = _profile(detail, profile)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "hits": [], "hit_count": 0}
    path = Path(index_path).expanduser().resolve() if index_path else default_index_path(vault)
    if not path.is_file():
        return {
            "ok": False,
            "error": f"index missing: {path}; run: agent-brain retrieve rebuild {vault}",
            "hits": [],
            "hit_count": 0,
        }

    clauses = ["records_fts MATCH ?"]
    params: list[Any] = [_fts_query(query)]
    for column, value in (
        ("project", project),
        ("record_type", record_type),
        ("state", state),
        ("freshness", freshness),
        ("scope", scope),
        ("risk_boundary", risk_boundary),
    ):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    generation_id, meta = _generation_meta(conn)
    try:
        try:
            offset = decode_cursor(cursor, generation_id, kind="search") if cursor else 0
        except CursorError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "hits": [],
                "hit_count": 0,
                "generation_id": generation_id,
            }
        try:
            rows = conn.execute(
                f"""
                SELECT record_id,path,project,record_type,memory_type,
                       coalesce(raw_title,title) AS title,
                       coalesce(raw_body,body) AS body,
                       state,freshness,scope,risk_boundary,updated_at,
                       bm25(records_fts) AS score
                FROM records_fts
                WHERE {' AND '.join(clauses)}
                """,
                params,
            ).fetchall()
        except sqlite3.OperationalError as exc:
            return {"ok": False, "error": str(exc), "hits": [], "hit_count": 0}
        all_items: list[dict[str, Any]] = []
        query_lower = query.lower()
        for row in rows:
            item = {key: row[key] for key in row.keys()}
            if not include_inactive and not is_active_for_context(item):
                continue
            title_lower = str(item.get("title") or "").lower()
            exact_title = bool(query_lower.strip()) and all(part in title_lower for part in re.findall(r"[\w\u4e00-\u9fff]+", query_lower))
            rank = _path_rank(str(item.get("path") or ""), vault)
            item["_sort"] = (0 if exact_title else 1, float(item.get("score") or 0.0) - 0.35 * rank, -rank, str(item.get("path") or ""))
            item["_rank"] = rank
            all_items.append(item)
        all_items.sort(key=lambda item: item["_sort"])
        total = len(all_items)
        page = all_items[offset : offset + max(1, min(int(limit), 200))]
        lim = max(1, min(int(limit), 200))
        coverage = _coverage_for_index(vault, path, generation_id, len(rows))
        hits: list[dict[str, Any]] = []
        for item in page:
            body = str(item.pop("body", "") or "")
            item.pop("_sort", None)
            item.pop("_rank", None)
            item["body_preview"] = body[:400]
            item["candidate_only"] = True
            item["reopen"] = str(vault / str(item.get("path") or ""))
            item["relation_summary"] = _relation_summary(conn, str(item.get("record_id") or ""))
            item["generation_id"] = generation_id
            item["coverage"] = coverage
            if selected_profile == "scout":
                item.pop("body_preview", None)
            elif selected_profile == "auditor":
                evidence = body[:4000]
                item["body_preview"] = evidence
                item["evidence"] = evidence
                item["truncated"] = len(body) > len(evidence)
                item["limitations"] = ["Derived ranking is candidate evidence only; reopen Markdown truth."]
            hits.append(item)
        has_more = offset + lim < total
        return {
            "ok": True,
            "derived": True,
            "canonical": "markdown",
            "index_path": str(path),
            "generation_id": generation_id,
            "coverage": coverage,
            "query": query,
            "fts_query": _fts_query(query),
            "profile": selected_profile,
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
            "total_count": total,
            "limit": lim,
            "has_more": has_more,
            "next_cursor": encode_cursor(generation_id, offset + lim, kind="search") if has_more else None,
            "hits": hits,
            "note": "Hits are retrieval candidates only. Reopen source Markdown before acting.",
        }
    finally:
        conn.close()


__all__ = ["search"]
