"""Locate repository assets (templates, schemas, scripts)."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def package_root() -> Path:
    return Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return checkout root when running from a git clone; else package parent chain."""
    # src/agent_brain/paths.py → src → repo
    candidate = package_root().parents[1]
    if (candidate / "templates" / "vault").is_dir() and (candidate / "scripts").is_dir():
        return candidate
    # Fallback: walk parents looking for markers
    for parent in package_root().parents:
        if (parent / "templates" / "vault").is_dir() and (parent / "schemas").is_dir():
            return parent
    return candidate


def scripts_dir() -> Path:
    return repo_root() / "scripts"


def ensure_scripts_on_path() -> Path:
    """Make legacy scripts/ and scripts/lib importable for CLI wrappers."""
    scripts = scripts_dir()
    text = str(scripts)
    if text not in sys.path:
        sys.path.insert(0, text)
    return scripts
