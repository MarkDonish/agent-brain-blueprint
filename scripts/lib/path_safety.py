"""Path containment helpers for vault-relative and project slug safety."""

from __future__ import annotations

import re
from pathlib import Path

# 1–64 chars; alphanumeric or unicode word/CJK, dots, hyphens, underscores.
# No separators, no parent refs, no absolute forms.
_PROJECT_SLUG_RE = re.compile(r"^[\w\u4e00-\u9fff][\w\u4e00-\u9fff._-]{0,63}$", re.UNICODE)


class PathSafetyError(ValueError):
    """Raised when a path or project slug is unsafe."""


def validate_project_slug(project: str) -> str:
    """Return a validated project folder name.

    Rejects empty values, absolute paths, parent escapes, separators, and
    control characters. Length is capped at 64.
    """
    if project is None:
        raise PathSafetyError("project slug is required")
    raw = str(project)
    if not raw or raw != raw.strip():
        raise PathSafetyError("project slug must be non-empty and unpadded")
    if any(ch in raw for ch in ("/", "\\", "\n", "\r", "\t", "\0")):
        raise PathSafetyError(f"project slug contains forbidden characters: {raw!r}")
    if raw in {".", ".."} or raw.startswith("~") or ".." in raw:
        raise PathSafetyError(f"project slug escapes or is reserved: {raw!r}")
    if len(raw) > 64:
        raise PathSafetyError("project slug must be at most 64 characters")
    if not _PROJECT_SLUG_RE.fullmatch(raw):
        raise PathSafetyError(
            "project slug must match [A-Za-z0-9_\\u4e00-\\u9fff][A-Za-z0-9._-\\u4e00-\\u9fff]{0,63}"
        )
    return raw


def safe_relative_path(root: Path, raw: str) -> str | None:
    """Return a vault-relative POSIX path if raw stays inside root, else None."""
    if raw is None:
        return None
    text = str(raw)
    if not text or text.startswith(("/", "~")) or "\\" in text:
        return None
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    try:
        root_resolved = root.resolve(strict=False)
        candidate = (root_resolved / text).resolve(strict=False)
        return str(candidate.relative_to(root_resolved)).replace("\\", "/")
    except (OSError, RuntimeError, ValueError):
        return None


def safe_vault_join(root: Path, *parts: str) -> Path:
    """Join parts under root and require the result stays inside the vault."""
    root_resolved = root.resolve(strict=False)
    candidate = root_resolved.joinpath(*parts).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSafetyError(f"path escapes vault root: {parts!r}") from exc
    return candidate


def project_dir(vault_root: Path, project: str) -> Path:
    """Return project directory under 10_projects/ or 10_项目工作区/ after validating slug."""
    slug = validate_project_slug(project)
    chinese_dir = safe_vault_join(vault_root, "10_项目工作区", slug)
    if chinese_dir.is_dir():
        return chinese_dir
    return safe_vault_join(vault_root, "10_projects", slug)
