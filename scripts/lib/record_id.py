"""Stable record identifiers (ULID-style, no third-party deps)."""

from __future__ import annotations

import os
import re
import time

# Crockford Base32 (no I, L, O, U)
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_RECORD_ID_RE = re.compile(r"^[a-z]{2,8}_[0-9A-HJKMNP-TV-Z]{26}$")


def _encode_crockford(value: int, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def generate_ulid(*, timestamp_ms: int | None = None, entropy: bytes | None = None) -> str:
    """Return a 26-char Crockford ULID (time-sortable, local generation)."""
    ts = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    if ts < 0 or ts >= (1 << 48):
        raise ValueError("timestamp_ms out of ULID range")
    rand = entropy if entropy is not None else os.urandom(10)
    if len(rand) != 10:
        raise ValueError("entropy must be 10 bytes")
    # 48-bit time + 80-bit randomness → 128 bits → 26 base32 chars
    value = (ts << 80) | int.from_bytes(rand, "big")
    return _encode_crockford(value, 26)


def new_record_id(prefix: str = "mem", **kwargs) -> str:
    """Return prefixed stable id, e.g. mem_01K..."""
    prefix = (prefix or "mem").strip().lower()
    if not re.fullmatch(r"[a-z]{2,8}", prefix):
        raise ValueError("prefix must be 2-8 lowercase letters")
    return f"{prefix}_{generate_ulid(**kwargs)}"


def is_valid_record_id(value: str) -> bool:
    return bool(value and _RECORD_ID_RE.fullmatch(str(value)))
