"""Minimal frontmatter field update helpers (no third-party YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def split_frontmatter(text: str) -> tuple[list[str], list[str], str]:
    """Return (open_delim_lines, fm_lines, body_including_closing_and_rest).

    For standard --- ... --- files, returns fm content lines without the fence lines,
    and body as everything after the closing --- (may start with newline).
    """
    if not text.startswith("---"):
        raise ValueError("missing frontmatter")
    lines = text.splitlines(keepends=True)
    if not lines:
        raise ValueError("empty file")
    # find closing
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("unterminated frontmatter")
    fm_lines = lines[1:end]
    rest = "".join(lines[end + 1 :])
    return [lines[0]], fm_lines, rest


def set_frontmatter_fields(text: str, updates: dict[str, Any]) -> str:
    """Set or replace top-level scalar frontmatter keys; list values become YAML lists."""
    open_line, fm_lines, rest = split_frontmatter(text)
    # Map key -> rendered line(s)
    keys_done: set[str] = set()
    out_fm: list[str] = []
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out_fm.append(line if line.endswith("\n") else line + "\n")
            i += 1
            continue
        if ":" in stripped and not stripped.startswith("-"):
            key = stripped.split(":", 1)[0].strip()
            # skip existing list block for this key if we will replace
            if key in updates:
                keys_done.add(key)
                # skip following indented list items belonging to this key
                i += 1
                while i < len(fm_lines) and (
                    fm_lines[i].startswith("  -")
                    or fm_lines[i].startswith("\t-")
                    or (fm_lines[i].startswith(" ") and fm_lines[i].lstrip().startswith("-"))
                ):
                    i += 1
                out_fm.extend(_render_field(key, updates[key]))
                continue
        out_fm.append(line if line.endswith("\n") else line + "\n")
        i += 1

    for key, value in updates.items():
        if key not in keys_done:
            out_fm.extend(_render_field(key, value))

    body = rest if rest.startswith("\n") else "\n" + rest
    return "---\n" + "".join(out_fm) + "---" + body


def _render_field(key: str, value: Any) -> list[str]:
    if isinstance(value, list):
        lines = [f"{key}:\n"]
        for item in value:
            lines.append(f"  - {item}\n")
        return lines
    if value is None:
        return [f"{key}: null\n"]
    if isinstance(value, bool):
        return [f"{key}: {'true' if value else 'false'}\n"]
    text = str(value)
    if "\n" in text:
        raise ValueError(f"multiline scalar not supported for {key}")
    return [f"{key}: {text}\n"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
