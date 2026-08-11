"""Load vault layout manifest (single source of truth for skeleton paths)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = REPO_ROOT / "schemas" / "vault_layout.json"


@lru_cache(maxsize=1)
def load_vault_layout() -> dict:
    return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))


def required_entries(*, project: bool = False) -> list[dict]:
    layout = load_vault_layout()
    key = "project_paths" if project else "paths"
    return [entry for entry in layout.get(key, []) if entry.get("required", True)]
