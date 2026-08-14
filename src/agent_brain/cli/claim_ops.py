"""Claim acquire / close helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_brain.paths import ensure_scripts_on_path, repo_root


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def acquire_claim(
    vault: Path,
    *,
    session_id: str,
    task: str,
    planned_paths: list[str],
    claimed_by: str = "agent-brain-cli",
    hours: int = 8,
    filename: str | None = None,
) -> Path:
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, safe_relative_path, safe_vault_join
    from lib.record_id import new_record_id

    root = vault.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault not found: {root}")
    if not session_id.strip():
        raise ValueError("session_id is required")
    if not task.strip():
        raise ValueError("task is required")
    if not planned_paths:
        raise ValueError("at least one planned path is required")

    safe_paths: list[str] = []
    for raw in planned_paths:
        safe = safe_relative_path(root, raw)
        if safe is None:
            raise PathSafetyError(f"unsafe planned path: {raw}")
        safe_paths.append(safe)

    claimed_at = datetime.now(timezone.utc).replace(microsecond=0)
    expires_at = claimed_at + timedelta(hours=max(1, hours))
    record_id = new_record_id("clm")

    lines = "\n".join(f"  - {p}" for p in safe_paths)
    body = f"""---
memory_type: session-handoff
record_type: claim
record_id: {record_id}
source: agent-brain claim acquire
confidence: pending
freshness: current
scope: project
risk_boundary: normal
next_review: before closeout
owner: {claimed_by}
claimed_by: {claimed_by}

session_id: {session_id}
task: {task}
claimed_at: {claimed_at.isoformat()}
expires_at: {expires_at.isoformat()}
status: active
planned_paths:
{lines}
dry_run_status: pending
dry_run_command: agent-brain claim gate --claim <this-file>
dry_run_evidence: pending
closeout_state: open
closeout_summary: Not closed
next_action: Run claim gate excluding self, then work planned paths
---

# Session claim

Created by `agent-brain claim acquire`. This is **not** a distributed lock.
Dry-run fields are self-attested. Re-run gate before contested writes:

```bash
agent-brain claim gate {root} --claim 40_handoffs/session_claims/{filename or "CLAIM.md"}
```
"""

    claims_dir = root / "40_handoffs" / "session_claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        stamp = claimed_at.strftime("%Y%m%d-%H%M%S")
        safe_sid = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in session_id)[:48]
        filename = f"{stamp}-{safe_sid}.md"
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise PathSafetyError(f"unsafe claim filename: {filename}")
    path = safe_vault_join(root, "40_handoffs", "session_claims", filename)
    if path.exists():
        raise FileExistsError(f"claim already exists: {path}")
    path.write_text(body, encoding="utf-8")
    return path


def close_claim(vault: Path, claim_rel_or_abs: str, *, summary: str = "Closed via agent-brain claim close") -> Path:
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, safe_relative_path, safe_vault_join

    root = vault.expanduser().resolve()
    raw = claim_rel_or_abs
    if Path(raw).is_absolute():
        path = Path(raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise PathSafetyError(f"claim path outside vault: {raw}") from exc
    else:
        rel = safe_relative_path(root, raw)
        if rel is None:
            raise PathSafetyError(f"unsafe claim path: {raw}")
        path = safe_vault_join(root, *rel.split("/"))
    if not path.is_file():
        raise FileNotFoundError(f"claim not found: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("claim file has no frontmatter")

    # Minimal field updates without a full YAML rewriter.
    replacements = {
        "status:": None,  # handled below
    }
    lines = text.splitlines()
    out: list[str] = []
    in_fm = False
    fm_done = False
    seen = {
        "status": False,
        "closeout_state": False,
        "closeout_summary": False,
        "closeout_at": False,
        "next_action": False,
    }
    closeout_at = _iso_now()
    for line in lines:
        if not fm_done and line.strip() == "---":
            if not in_fm:
                in_fm = True
                out.append(line)
                continue
            # closing frontmatter — inject missing keys
            if not seen["status"]:
                out.append("status: closed")
            if not seen["closeout_state"]:
                out.append("closeout_state: closed")
            if not seen["closeout_summary"]:
                out.append(f"closeout_summary: {summary}")
            if not seen["closeout_at"]:
                out.append(f"closeout_at: {closeout_at}")
            if not seen["next_action"]:
                out.append("next_action: none")
            out.append(line)
            fm_done = True
            in_fm = False
            continue
        if in_fm:
            if line.startswith("status:"):
                out.append("status: closed")
                seen["status"] = True
                continue
            if line.startswith("closeout_state:"):
                out.append("closeout_state: closed")
                seen["closeout_state"] = True
                continue
            if line.startswith("closeout_summary:"):
                out.append(f"closeout_summary: {summary}")
                seen["closeout_summary"] = True
                continue
            if line.startswith("closeout_at:"):
                out.append(f"closeout_at: {closeout_at}")
                seen["closeout_at"] = True
                continue
            if line.startswith("next_action:"):
                out.append("next_action: none")
                seen["next_action"] = True
                continue
        out.append(line)
    path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return path


def renew_claim(
    vault: Path, claim_rel_or_abs: str, *, hours: int = 8
) -> Path:
    ensure_scripts_on_path()
    from lib.path_safety import PathSafetyError, safe_relative_path, safe_vault_join

    root = vault.expanduser().resolve()
    raw = claim_rel_or_abs
    if Path(raw).is_absolute():
        path = Path(raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise PathSafetyError(f"claim path outside vault: {raw}") from exc
    else:
        rel = safe_relative_path(root, raw)
        if rel is None:
            raise PathSafetyError(f"unsafe claim path: {raw}")
        path = safe_vault_join(root, *rel.split("/"))
    if not path.is_file():
        raise FileNotFoundError(f"claim not found: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("claim file has no frontmatter")

    new_expires = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=max(1, hours))
    ).isoformat()

    lines = text.splitlines()
    out: list[str] = []
    in_fm = False
    for line in lines:
        if line.strip() == "---":
            in_fm = not in_fm
            out.append(line)
            continue
        if in_fm and line.startswith("expires_at:"):
            out.append(f"expires_at: {new_expires}")
            continue
        if in_fm and line.startswith("status:"):
            out.append("status: active")
            continue
        out.append(line)

    path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return path


def prune_claims(vault: Path, *, dry_run: bool = False) -> list[dict[str, Any]]:
    ensure_scripts_on_path()
    from lib.frontmatter import parse_frontmatter

    root = vault.expanduser().resolve()
    claims_dir = root / "40_handoffs" / "session_claims"
    if not claims_dir.is_dir():
        return []

    now = datetime.now(timezone.utc).replace(microsecond=0)
    pruned: list[dict[str, Any]] = []

    for path in sorted(claims_dir.glob("*.md")):
        if not path.is_file():
            continue
        try:
            data, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        status = str(data.get("status") or "")
        expires_raw = str(data.get("expires_at") or "")
        if status == "active" and expires_raw:
            try:
                exp_dt = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if exp_dt < now:
                    rel = str(path.relative_to(root))
                    pruned.append({
                        "path": rel,
                        "session_id": data.get("session_id"),
                        "expired_at": expires_raw,
                    })
                    if not dry_run:
                        close_claim(root, rel, summary="Auto-pruned expired claim")
            except Exception:
                continue

    return pruned


def template_path() -> Path:
    return repo_root() / "templates" / "session_claim.md"

