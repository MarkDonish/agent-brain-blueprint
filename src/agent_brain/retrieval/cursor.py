"""Small, opaque cursors for deterministic derived-index pagination.

Cursors intentionally carry the generation identifier.  A cursor from an old
generation is never silently applied to a newly published index: callers get a
closed failure and can start a fresh page from the current generation.
"""

from __future__ import annotations

import base64
import json
from typing import Any


class CursorError(ValueError):
    """Raised when a cursor is malformed or belongs to another generation."""


def encode_cursor(generation_id: str, offset: int, *, kind: str = "search") -> str:
    payload = {"v": 1, "generation": str(generation_id), "offset": max(0, int(offset)), "kind": kind}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, generation_id: str, *, kind: str = "search") -> int:
    if not cursor or not isinstance(cursor, str):
        raise CursorError("cursor is empty")
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload: Any = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise CursorError("invalid cursor") from exc
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise CursorError("unsupported cursor")
    if str(payload.get("generation")) != str(generation_id):
        raise CursorError("cursor generation mismatch")
    if str(payload.get("kind", "search")) != kind:
        raise CursorError("cursor kind mismatch")
    try:
        offset = int(payload.get("offset", 0))
    except (TypeError, ValueError) as exc:
        raise CursorError("invalid cursor offset") from exc
    if offset < 0:
        raise CursorError("invalid cursor offset")
    return offset


__all__ = ["CursorError", "decode_cursor", "encode_cursor"]
