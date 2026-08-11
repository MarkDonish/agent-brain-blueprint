"""Derived retrieval layer (SQLite FTS5). Not a source of truth."""

from agent_brain.retrieval.index import default_index_path, rebuild_index
from agent_brain.retrieval.query import search

__all__ = ["default_index_path", "rebuild_index", "search"]
