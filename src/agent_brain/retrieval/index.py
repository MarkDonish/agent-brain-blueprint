"""Immutable, rebuildable retrieval generations for an Agent-Brain vault.

Markdown is canonical. Everything under ``50_retrieval/indexes`` is derived
and may be removed. A generation is built in a sibling staging directory,
validated, renamed into ``generations/``, and made visible by an atomic
``current.json`` replacement. A failed build therefore leaves both the old
pointer and canonical Markdown untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Callable

from agent_brain.layout import detect_layout
from agent_brain.retrieval.generations import (
    build_lock,
    generation_id,
    run_failure_hook,
    utc_now,
    write_json_atomic,
)
from agent_brain.retrieval.graph import build_graph
from agent_brain.retrieval.scan import scan_records, source_inventory

INDEX_REL = "50_retrieval/indexes/fts.sqlite"
CURRENT_NAME = "current.json"
GENERATION_DIR = "generations"
SCHEMA_VERSION = "3"


def _utc_now() -> str:
    return utc_now()


def _layout_and_root(vault: Path):
    layout = detect_layout(vault)
    return layout, layout.path(vault, "retrieval_root") / "indexes"


def _read_current(vault: Path) -> dict[str, Any] | None:
    try:
        _layout, root = _layout_and_root(vault)
        pointer = root / CURRENT_NAME
        data = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("generation_id"):
        return None
    generation_id = str(data["generation_id"])
    generation_rel = str(data.get("generation_path") or f"{GENERATION_DIR}/{generation_id}")
    generation = (root / generation_rel).resolve()
    try:
        generation.relative_to(root.resolve())
    except ValueError:
        return None
    index = generation / "fts.sqlite"
    manifest = generation / "manifest.json"
    if not index.is_file() or not manifest.is_file():
        return None
    result = dict(data)
    result.update(
        {
            "generation_id": generation_id,
            "generation_path": generation_rel,
            "index_path": str(index),
            "manifest_path": str(manifest),
        }
    )
    return result


def default_index_path(vault: Path) -> Path:
    """Resolve the current immutable generation, with legacy fallback."""

    vault = vault.expanduser().resolve()
    current = _read_current(vault)
    if current:
        return Path(str(current["index_path"]))
    try:
        _layout, root = _layout_and_root(vault)
        # A present-but-invalid current pointer is a fail-closed state. The
        # legacy fallback is only for vaults that have no pointer at all.
        if (root / CURRENT_NAME).exists():
            return root / ".invalid-current" / "fts.sqlite"
        return root / "fts.sqlite"
    except Exception:
        # Preserve the historical path for callers probing a partial fixture.
        return vault / INDEX_REL


def current_generation(vault: Path) -> dict[str, Any] | None:
    """Return current pointer plus manifest without rebuilding or mutating."""

    vault = vault.expanduser().resolve()
    current = _read_current(vault)
    if not current:
        return None
    try:
        manifest = json.loads(Path(current["manifest_path"]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if isinstance(manifest, dict):
        current["manifest"] = manifest
    return current


def _normalize_cjk(text: str) -> str:
    """Insert spaces around CJK characters for unicode61 FTS5 indexing."""

    if not text:
        return ""
    return re.sub(r"([\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af])", r" \1 ", text)


def _records_with_sources(vault: Path, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    source_by_path = {item["path"]: item for item in inventory["eligible"]}
    records = scan_records(vault)
    for record in records:
        source = source_by_path.get(record.get("path"))
        if source:
            record["source_fingerprint"] = source.get("fingerprint", "")
            record["source_size"] = source.get("size", 0)
            record["source_mtime"] = source.get("mtime", 0.0)
    return records


def _project_names(vault: Path, layout, records: list[dict[str, Any]]) -> list[str]:
    names = {str(record.get("project") or "") for record in records if record.get("project")}
    root = layout.path(vault, "projects_root")
    if root.is_dir():
        names.update(path.name for path in root.iterdir() if path.is_dir() and path.name not in {".git", "indexes"})
    return sorted(name for name in names if name)


def _create_sqlite(
    vault: Path,
    sqlite_path: Path,
    *,
    records: list[dict[str, Any]],
    inventory: dict[str, Any],
    generation_id: str,
    layout_id: str,
    projects: list[str] | None = None,
) -> dict[str, int]:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path))
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
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
              source_fingerprint UNINDEXED,
              source_size UNINDEXED,
              source_mtime UNINDEXED,
              tokenize = 'unicode61'
            )
            """
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO meta(key,value) VALUES (?,?)",
            [
                ("kind", "agent-brain-fts"),
                ("version", SCHEMA_VERSION),
                ("schema_version", SCHEMA_VERSION),
                ("generation_id", generation_id),
                ("layout_id", layout_id),
            ],
        )
        rows = [
            (
                _normalize_cjk(str(r.get("title") or "")),
                _normalize_cjk(str(r.get("body") or "")),
                str(r.get("title") or ""),
                str(r.get("body") or ""),
                str(r.get("path") or ""),
                str(r.get("record_id") or ""),
                str(r.get("project") or ""),
                str(r.get("record_type") or ""),
                str(r.get("memory_type") or ""),
                str(r.get("state") or ""),
                str(r.get("freshness") or ""),
                str(r.get("scope") or ""),
                str(r.get("risk_boundary") or ""),
                str(r.get("updated_at") or ""),
                str(r.get("source_fingerprint") or ""),
                int(r.get("source_size") or 0),
                float(r.get("source_mtime") or 0.0),
            )
            for r in records
        ]
        conn.executemany(
            """
            INSERT INTO records_fts(
              title,body,raw_title,raw_body,path,record_id,project,record_type,memory_type,
              state,freshness,scope,risk_boundary,updated_at,source_fingerprint,source_size,source_mtime
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        graph_counts = build_graph(
            conn,
            records,
            projects=projects or sorted({str(r.get("project") or "") for r in records if r.get("project")}),
        )
        conn.commit()
        return graph_counts
    finally:
        conn.close()


def _manifest(
    *,
    vault: Path,
    layout_id: str,
    generation_id: str,
    inventory: dict[str, Any],
    records: list[dict[str, Any]],
    graph_counts: dict[str, int],
) -> dict[str, Any]:
    files = [
        {
            "path": str(item["path"]),
            "fingerprint": str(item.get("fingerprint") or ""),
            "size": int(item.get("size") or 0),
            "mtime": float(item.get("mtime") or 0.0),
            "mtime_ns": int(item.get("mtime_ns") or 0),
        }
        for item in inventory["eligible"]
    ]
    aggregate = hashlib.sha256(
        "\n".join(
            f"{item['path']}\0{item['fingerprint']}\0{item['size']}\0{item['mtime_ns']}"
            for item in files
        ).encode("utf-8")
    ).hexdigest()
    total_size = sum(int(item["size"]) for item in files)
    latest_mtime = max((float(item["mtime"]) for item in files), default=0.0)
    return {
        "manifest_version": 1,
        "generation_id": generation_id,
        "created_at": _utc_now(),
        "layout_id": layout_id,
        "index_file": "fts.sqlite",
        "source_count": int(inventory["source_count"]),
        "indexed_count": int(len(records)),
        "blocked_source_count": int(inventory["blocked_source_count"]),
        "source_fingerprint": aggregate,
        "source_size": total_size,
        "source_mtime": latest_mtime,
        "source": {
            "count": int(inventory["source_count"]),
            "indexed_count": int(len(records)),
            "blocked_count": int(inventory["blocked_source_count"]),
            "fingerprint": aggregate,
            "size": total_size,
            "mtime": latest_mtime,
            "files": files,
            "blocked_paths": [str(item["path"]) for item in inventory["blocked"]],
        },
        "coverage": {
            "source_count": int(inventory["source_count"]),
            "indexed_count": int(len(records)),
            "blocked_source_count": int(inventory["blocked_source_count"]),
            "definition": "complete only when every eligible Markdown source is indexed and no blocked Markdown is present; blocked paths are disclosed, never silently counted",
        },
        "relations": dict(graph_counts),
        "record_paths": [str(r.get("path") or "") for r in records],
        "canonical": "markdown",
        "derived": True,
    }


def _validate_generation(generation: Path, manifest: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    manifest_path = generation / "manifest.json"
    index_path = generation / "fts.sqlite"
    if manifest is None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return False, [f"manifest invalid: {exc}"]
    if not isinstance(manifest, dict):
        return False, ["manifest is not an object"]
    if not manifest.get("generation_id") or not index_path.is_file():
        errors.append("generation pointer or fts.sqlite missing")
    if not index_path.is_file():
        return False, errors
    conn = None
    try:
        conn = sqlite3.connect(str(index_path))
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            errors.append(f"sqlite integrity: {integrity}")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        for table in ("records_fts", "meta", "nodes", "relations"):
            if table not in tables:
                errors.append(f"sqlite schema missing: {table}")
        meta = dict(conn.execute("SELECT key,value FROM meta").fetchall()) if "meta" in tables else {}
        if str(meta.get("generation_id", "")) != str(manifest.get("generation_id", "")):
            errors.append("sqlite generation_id mismatch")
        if str(meta.get("layout_id", "")) != str(manifest.get("layout_id", "")):
            errors.append("sqlite layout_id mismatch")
        if "records_fts" in tables:
            record_count = int(conn.execute("SELECT count(*) FROM records_fts").fetchone()[0])
            if record_count != int(manifest.get("indexed_count", record_count)):
                errors.append("manifest indexed_count mismatch")
        relation_meta = manifest.get("relations") if isinstance(manifest.get("relations"), dict) else {}
        if "nodes" in tables and relation_meta.get("node_count") is not None:
            node_count = int(conn.execute("SELECT count(*) FROM nodes").fetchone()[0])
            if node_count != int(relation_meta.get("node_count")):
                errors.append("manifest node_count mismatch")
        if "relations" in tables and relation_meta.get("relation_count") is not None:
            edge_count = int(conn.execute("SELECT count(*) FROM relations").fetchone()[0])
            if edge_count != int(relation_meta.get("relation_count")):
                errors.append("manifest relation_count mismatch")
    except (sqlite3.Error, OSError) as exc:
        errors.append(f"sqlite invalid: {exc}")
    finally:
        if conn is not None:
            conn.close()
    return not errors, errors


def _publish_generation(
    vault: Path,
    *,
    layout_id: str,
    inventory: dict[str, Any],
    records: list[dict[str, Any]],
    lock_timeout: float,
    failure_inject: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    _layout, index_root = _layout_and_root(vault)
    generations = index_root / GENERATION_DIR
    generations.mkdir(parents=True, exist_ok=True)
    new_generation_id = generation_id()
    staging = index_root / f".staging-{new_generation_id}"
    final = generations / new_generation_id
    with build_lock(index_root, timeout=lock_timeout):
        try:
            staging.mkdir()
            graph_counts = _create_sqlite(
                vault,
                staging / "fts.sqlite",
                records=records,
                inventory=inventory,
                generation_id=new_generation_id,
                layout_id=layout_id,
                projects=_project_names(vault, detect_layout(vault), records),
            )
            manifest = _manifest(
                vault=vault,
                layout_id=layout_id,
                generation_id=new_generation_id,
                inventory=inventory,
                records=records,
                graph_counts=graph_counts,
            )
            write_json_atomic(staging / "manifest.json", manifest)
            run_failure_hook(failure_inject, "validate")
            valid, errors = _validate_generation(staging, manifest)
            if not valid:
                raise RuntimeError("generation validation failed: " + "; ".join(errors))
            run_failure_hook(failure_inject, "before_publish")
            os.replace(staging, final)
            run_failure_hook(failure_inject, "after_generation")
            pointer = {
                "pointer_version": 1,
                "generation_id": new_generation_id,
                "layout_id": layout_id,
                "generation_path": f"{GENERATION_DIR}/{new_generation_id}",
                "index_path": f"{GENERATION_DIR}/{new_generation_id}/fts.sqlite",
                "manifest_path": f"{GENERATION_DIR}/{new_generation_id}/manifest.json",
                "published_at": _utc_now(),
            }
            write_json_atomic(index_root / CURRENT_NAME, pointer)
            run_failure_hook(failure_inject, "after_pointer")
            return {
                "generation_id": new_generation_id,
                "index_path": str(final / "fts.sqlite"),
                "manifest_path": str(final / "manifest.json"),
                "manifest": manifest,
                "published": True,
            }
        except Exception:
            # A final generation is healthy even if pointer publication fails;
            # retain it for diagnostics and remove only unexposed staging.
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise


def rebuild_index(
    vault: Path,
    *,
    index_path: Path | None = None,
    lock_timeout: float = 10.0,
    failure_inject: Callable[[str], Any] | None = None,
    failure_at: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Build and publish a complete generation, or preserve explicit path API."""

    vault = vault.expanduser().resolve()
    if timeout is not None:
        lock_timeout = float(timeout)
    if not vault.is_dir():
        raise FileNotFoundError(f"vault not found: {vault}")
    layout, _index_root = _layout_and_root(vault)
    inventory = source_inventory(vault)
    records = _records_with_sources(vault, inventory)
    if index_path is not None:
        # Explicit paths remain compatible with existing integrations/tests and
        # do not move the vault's current pointer.
        target = Path(index_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.tmp-{uuid.uuid4().hex}")
        explicit_generation_id = generation_id()
        try:
            graph_counts = _create_sqlite(
                vault,
                tmp,
                records=records,
                inventory=inventory,
                generation_id=explicit_generation_id,
                layout_id=layout.layout_id,
                projects=_project_names(vault, layout, records),
            )
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        manifest = _manifest(
            vault=vault,
            layout_id=layout.layout_id,
            generation_id=explicit_generation_id,
            inventory=inventory,
            records=records,
            graph_counts=graph_counts,
        )
        return {
            "vault": str(vault),
            "index_path": str(target),
            "record_count": len(records),
            "source_count": inventory["source_count"],
            "indexed_count": len(records),
            "blocked_source_count": inventory["blocked_source_count"],
            "generation_id": explicit_generation_id,
            "manifest": manifest,
            "published": True,
            "derived": True,
            "rebuildable": True,
            "canonical": "markdown",
        }
    if failure_at and failure_inject is None:
        failure_inject = lambda stage: (_ for _ in ()).throw(RuntimeError(f"injected failure at {stage}")) if stage == failure_at else None
    published = _publish_generation(
        vault,
        layout_id=layout.layout_id,
        inventory=inventory,
        records=records,
        lock_timeout=lock_timeout,
        failure_inject=failure_inject,
    )
    manifest = published["manifest"]
    return {
        "vault": str(vault),
        "index_path": published["index_path"],
        "manifest_path": published["manifest_path"],
        "record_count": len(records),
        "source_count": inventory["source_count"],
        "indexed_count": len(records),
        "blocked_source_count": inventory["blocked_source_count"],
        "generation_id": published["generation_id"],
        "manifest": manifest,
        "published": True,
        "derived": True,
        "rebuildable": True,
        "canonical": "markdown",
    }


def _manifest_for_current(vault: Path) -> tuple[dict[str, Any] | None, Path | None, str]:
    # Distinguish a malformed/broken current pointer from an absent pointer:
    # the former must not silently fall back to a legacy index in status or
    # refresh, otherwise a damaged generation could look healthy.
    try:
        _layout, root = _layout_and_root(vault)
        pointer_path = root / CURRENT_NAME
    except Exception:
        pointer_path = None
    current = _read_current(vault)
    if current:
        try:
            manifest = json.loads(Path(current["manifest_path"]).read_text(encoding="utf-8"))
            return manifest, Path(current["index_path"]), str(current["generation_id"])
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None, Path(current["index_path"]), str(current["generation_id"])
    if pointer_path is not None and pointer_path.is_file():
        return None, None, ""
    legacy = default_index_path(vault)
    if legacy.is_file():
        return None, legacy, "legacy"
    return None, legacy, ""


def _source_maps(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return {}
    source = manifest.get("source")
    files = source.get("files") if isinstance(source, dict) else manifest.get("files")
    return {str(item.get("path")): dict(item) for item in files or [] if isinstance(item, dict) and item.get("path")}


def _coverage(vault: Path, manifest: dict[str, Any] | None, *, current_valid: bool) -> dict[str, Any]:
    inventory = source_inventory(vault)
    actual = {str(item["path"]): item for item in inventory["eligible"]}
    expected = _source_maps(manifest)
    missing = sorted(path for path in expected if path not in actual)
    stale = sorted(
        path
        for path in expected
        if path in actual and str(expected[path].get("fingerprint", "")) != str(actual[path].get("fingerprint", ""))
    )
    source_count = len(actual)
    indexed_count = int(manifest.get("indexed_count", manifest.get("source_count", 0))) if manifest else 0
    blocked_count = int(inventory["blocked_source_count"])
    complete = bool(current_valid and not missing and not stale and indexed_count == source_count and blocked_count == 0)
    return {
        "source_count": source_count,
        "indexed_count": indexed_count,
        "missing_source_count": len(missing),
        "stale_source_count": len(stale),
        "blocked_source_count": blocked_count,
        "missing_paths": missing,
        "stale_paths": stale,
        "blocked_paths": [str(item["path"]) for item in inventory["blocked"]],
        "coverage_complete": complete,
    }


def status_index(vault: Path) -> dict[str, Any]:
    """Read-only current-generation and live source coverage status."""

    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"vault not found: {vault}")
    try:
        layout, _root = _layout_and_root(vault)
        layout_id = layout.layout_id
    except Exception as exc:
        return {"ok": False, "error": str(exc), "current_valid": False, "coverage_complete": False}
    manifest, index_path, generation_id = _manifest_for_current(vault)
    current_valid = False
    if manifest and index_path and index_path.is_file():
        current_valid, _errors = _validate_generation(index_path.parent, manifest)
    coverage = _coverage(vault, manifest, current_valid=current_valid)
    return {
        "ok": True,
        "generation_id": generation_id or None,
        "layout_id": str(manifest.get("layout_id") if manifest else layout_id),
        "index_path": str(index_path) if index_path else None,
        "source_count": coverage["source_count"],
        "indexed_count": coverage["indexed_count"],
        "missing_source_count": coverage["missing_source_count"],
        "stale_source_count": coverage["stale_source_count"],
        "blocked_source_count": coverage["blocked_source_count"],
        "blocked_paths": coverage["blocked_paths"],
        "coverage_complete": coverage["coverage_complete"],
        "current_valid": current_valid,
        "derived": True,
        "canonical": "markdown",
    }


def check_index(vault: Path) -> dict[str, Any]:
    """Read-only validation of pointer, manifest, SQLite schema and coverage."""

    vault = vault.expanduser().resolve()
    errors: list[str] = []
    try:
        _layout, root = _layout_and_root(vault)
    except Exception as exc:
        return {"ok": False, "passed": False, "errors": [str(exc)], "coverage_complete": False}
    pointer_path = root / CURRENT_NAME
    if not pointer_path.is_file():
        legacy = root / "fts.sqlite"
        if legacy.is_file():
            # Legacy files remain checkable; they cannot claim immutable
            # generation coverage because there is no source manifest.
            return {
                "ok": True,
                "passed": True,
                "legacy": True,
                "current_valid": True,
                "coverage_complete": False,
                "errors": [],
                "index_path": str(legacy),
            }
        return {"ok": False, "passed": False, "errors": ["current.json missing"], "current_valid": False, "coverage_complete": False}
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "passed": False, "errors": [f"pointer invalid: {exc}"], "current_valid": False, "coverage_complete": False}
    if not isinstance(pointer, dict) or not pointer.get("generation_id"):
        errors.append("pointer missing generation_id")
        return {"ok": False, "passed": False, "errors": errors, "current_valid": False, "coverage_complete": False}
    generation_rel = str(pointer.get("generation_path") or f"{GENERATION_DIR}/{pointer['generation_id']}")
    generation = (root / generation_rel).resolve()
    try:
        generation.relative_to(root.resolve())
    except ValueError:
        errors.append("pointer generation escapes retrieval root")
        return {"ok": False, "passed": False, "errors": errors, "current_valid": False, "coverage_complete": False}
    if generation.name != str(pointer.get("generation_id")):
        errors.append("pointer generation_id/path mismatch")
    try:
        manifest = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"manifest invalid: {exc}")
        manifest = None
    valid, generation_errors = _validate_generation(generation, manifest)
    errors.extend(generation_errors)
    coverage = _coverage(vault, manifest, current_valid=valid)
    if coverage["missing_source_count"] or coverage["stale_source_count"]:
        errors.append("source coverage differs from current manifest")
    if coverage["indexed_count"] != coverage["source_count"]:
        errors.append("indexed_count differs from eligible source_count")
    passed = not errors
    return {
        "ok": passed,
        "passed": passed,
        "errors": errors,
        "current_valid": valid,
        "coverage_complete": coverage["coverage_complete"] if passed else False,
        "generation_id": str(pointer.get("generation_id")),
        "layout_id": str(manifest.get("layout_id")) if isinstance(manifest, dict) else None,
        "index_path": str(generation / "fts.sqlite"),
        **{
            key: coverage[key]
            for key in (
                "source_count",
                "indexed_count",
                "missing_source_count",
                "stale_source_count",
                "blocked_source_count",
                "blocked_paths",
            )
        },
    }


def refresh_index(
    vault: Path,
    *,
    lock_timeout: float = 10.0,
    changed_limit: int = 100,
    failure_inject: Callable[[str], Any] | None = None,
    failure_at: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Publish a complete generation only when the eligible source set changed."""

    vault = vault.expanduser().resolve()
    if timeout is not None:
        lock_timeout = float(timeout)
    manifest, current_path, old_generation = _manifest_for_current(vault)
    inventory = source_inventory(vault)
    old_sources = _source_maps(manifest)
    current_sources = {str(item["path"]): item for item in inventory["eligible"]}
    added = sorted(set(current_sources) - set(old_sources))
    deleted = sorted(set(old_sources) - set(current_sources))
    modified = sorted(
        path
        for path in set(current_sources) & set(old_sources)
        if str(current_sources[path].get("fingerprint", "")) != str(old_sources[path].get("fingerprint", ""))
    )
    unchanged = sorted(set(current_sources) & set(old_sources) - set(modified))
    changed = added + modified + deleted
    report: dict[str, Any] = {
        "ok": True,
        "added": len(added),
        "modified": len(modified),
        "deleted": len(deleted),
        "unchanged": len(unchanged),
        "added_paths": added[:changed_limit],
        "modified_paths": modified[:changed_limit],
        "deleted_paths": deleted[:changed_limit],
        "changed_paths": changed[:changed_limit],
        "changed_paths_truncated": len(changed) > changed_limit,
        "previous_generation_id": old_generation or None,
        "published": False,
        "derived": True,
        "canonical": "markdown",
    }
    current_valid = bool(manifest and current_path and current_path.is_file() and _validate_generation(current_path.parent, manifest)[0])
    if not changed and manifest and old_generation and current_valid:
        report["no_op"] = True
        report["generation_id"] = old_generation
        report["coverage_complete"] = _coverage(vault, manifest, current_valid=True)["coverage_complete"]
        return report
    layout, _root = _layout_and_root(vault)
    records = _records_with_sources(vault, inventory)
    if failure_at and failure_inject is None:
        failure_inject = lambda stage: (_ for _ in ()).throw(RuntimeError(f"injected failure at {stage}")) if stage == failure_at else None
    published = _publish_generation(
        vault,
        layout_id=layout.layout_id,
        inventory=inventory,
        records=records,
        lock_timeout=lock_timeout,
        failure_inject=failure_inject,
    )
    report.update(
        {
            "no_op": False,
            "published": True,
            "generation_id": published["generation_id"],
            "index_path": published["index_path"],
            "manifest_path": published["manifest_path"],
        }
    )
    return report


status = status_index
check = check_index
refresh = refresh_index


__all__ = [
    "INDEX_REL",
    "build_lock",
    "check",
    "check_index",
    "current_generation",
    "default_index_path",
    "rebuild_index",
    "refresh",
    "refresh_index",
    "status",
    "status_index",
]
