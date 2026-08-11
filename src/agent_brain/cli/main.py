#!/usr/bin/env python3
"""agent-brain unified CLI (0.7.0).

Vault remains the data plane. This CLI is the runtime/tooling surface.
Legacy `python scripts/*.py` entrypoints stay as compatibility wrappers.
Retrieval indexes are derived/rebuildable and never canonical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_brain import __version__
from agent_brain.cli.claim_ops import acquire_claim, close_claim
from agent_brain.cli.project_ops import add_project, list_projects
from agent_brain.cli.runner import run_script
from agent_brain.context.builder import build_context
from agent_brain.paths import ensure_scripts_on_path, repo_root
from agent_brain.retrieval.index import rebuild_index
from agent_brain.retrieval.query import search


def _cmd_init(args: argparse.Namespace) -> int:
    dest = str(args.destination)
    project = args.project
    argv = ["--destination", dest, "--project", project]
    return run_script("bootstrap", argv)


def _cmd_doctor(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    if args.json:
        argv.append("--json")
    if args.strict:
        argv.append("--strict")
    if args.project:
        argv.extend(["--project", args.project])
    return run_script("doctor", argv)


def _cmd_privacy(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.root)]
    if args.strict:
        argv.append("--strict")
    return run_script("check_privacy_scan", argv)


def _cmd_migrate(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    argv = [str(vault)]
    if args.force:
        argv.append("--force")
    code = run_script("write_vault_manifest", argv)
    if code != 0:
        return code
    if args.apply_structure:
        fix_argv = [str(vault), "--apply"]
        if args.project:
            fix_argv.extend(["--project", args.project])
        return run_script("fix_vault_structure", fix_argv)
    print("manifest written; run with --apply-structure to create missing skeleton paths")
    return 0


def _cmd_record_validate(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    if args.strict_soft:
        argv.append("--strict-soft")
    if args.no_soft:
        argv.append("--no-soft")
    return run_script("check_memory_governance", argv)


def _cmd_record_id(args: argparse.Namespace) -> int:
    ensure_scripts_on_path()
    from lib.record_id import new_record_id

    print(new_record_id(args.prefix))
    return 0


def _cmd_project_list(args: argparse.Namespace) -> int:
    projects = list_projects(Path(args.vault))
    if not projects:
        print("(no projects under 10_projects/)")
        return 0
    for name in projects:
        print(name)
    return 0


def _cmd_project_add(args: argparse.Namespace) -> int:
    try:
        dest = add_project(Path(args.vault), args.name)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"created project: {dest}")
    return 0


def _cmd_claim_gate(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    for path in args.paths or []:
        argv.extend(["--path", path])
    if args.session_id:
        argv.extend(["--session-id", args.session_id])
    if args.claim:
        argv.extend(["--claim", args.claim])
    if args.ignore_invalid_claims:
        argv.append("--ignore-invalid-claims")
    if args.fail_on_expired:
        argv.append("--fail-on-expired")
    return run_script("check_claim_gate", argv)


def _cmd_claim_status(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    if args.fail_on_expired:
        argv.append("--fail-on-expired")
    return run_script("check_session_claims", argv)


def _cmd_claim_acquire(args: argparse.Namespace) -> int:
    try:
        path = acquire_claim(
            Path(args.vault),
            session_id=args.session_id,
            task=args.task,
            planned_paths=list(args.paths or []),
            claimed_by=args.claimed_by,
            hours=args.hours,
            filename=args.filename,
        )
    except Exception as exc:  # noqa: BLE001 — surface clean CLI errors
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"created claim: {path}")
    print("next: agent-brain claim gate <vault> --claim <relative-claim-path>")
    return 0


def _cmd_claim_close(args: argparse.Namespace) -> int:
    try:
        path = close_claim(Path(args.vault), args.claim, summary=args.summary)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"closed claim: {path}")
    return 0


def _cmd_format(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    if args.require_manifest:
        argv.append("--require-manifest")
    return run_script("check_vault_format", argv)


def _cmd_structure_fix(args: argparse.Namespace) -> int:
    argv: list[str] = [str(args.vault)]
    if args.project:
        argv.extend(["--project", args.project])
    if args.apply:
        argv.append("--apply")
    return run_script("fix_vault_structure", argv)


def _cmd_deferred(name: str, version: str) -> int:
    print(
        f"`agent-brain {name}` is planned for {version}. "
        "Use Markdown + doctor/claim tools until then.",
        file=sys.stderr,
    )
    return 2


def _cmd_retrieve_rebuild(args: argparse.Namespace) -> int:
    try:
        report = rebuild_index(Path(args.vault))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


def _cmd_retrieve_search(args: argparse.Namespace) -> int:
    result = search(
        Path(args.vault),
        args.query,
        project=args.project,
        record_type=args.record_type,
        state=args.state,
        freshness=args.freshness,
        scope=args.scope,
        risk_boundary=args.risk_boundary,
        include_inactive=args.include_inactive,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


def _cmd_context_build(args: argparse.Namespace) -> int:
    try:
        pack = build_context(
            Path(args.vault),
            project=args.project,
            task=args.task or "",
            max_tokens=args.max_tokens,
            rebuild_if_missing=not args.no_rebuild,
            fts_limit=args.fts_limit,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        # omit huge document duplication if meta-only requested
        out = dict(pack)
        if args.meta_only:
            out.pop("document", None)
        print(json.dumps(out, indent=2))
    else:
        print(pack["document"])
        if args.write:
            path = Path(args.write)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pack["document"], encoding="utf-8")
            print(f"\n# wrote {path}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-brain",
        description="Local-first multi-agent memory vault tooling (Markdown remains canonical).",
    )
    parser.add_argument("--version", action="version", version=f"agent-brain {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="bootstrap a new vault from the public template")
    p.add_argument("--destination", required=True, type=Path)
    p.add_argument("--project", default="example-app")
    p.set_defaults(func=_cmd_init)

    # doctor
    p = sub.add_parser("doctor", help="run format + structure + governance + claims")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--project", default=None)
    p.set_defaults(func=_cmd_doctor)

    # format
    p = sub.add_parser("format", help="check vault format / manifest version")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--require-manifest", action="store_true")
    p.set_defaults(func=_cmd_format)

    # privacy
    p = sub.add_parser("privacy", help="privacy scan (secrets redacted in output)")
    p.add_argument("root", nargs="?", type=Path, default=Path("."))
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=_cmd_privacy)

    # migrate
    p = sub.add_parser("migrate", help="write vault manifest; optional skeleton repair")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--force", action="store_true", help="overwrite existing manifest")
    p.add_argument("--apply-structure", action="store_true", help="also fix_vault_structure --apply")
    p.add_argument("--project", default=None, help="with --apply-structure, ensure one project skeleton")
    p.set_defaults(func=_cmd_migrate)

    # structure fix
    p = sub.add_parser("structure-fix", help="create missing skeleton paths (dry-run default)")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--project", default=None)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=_cmd_structure_fix)

    # project
    proj = sub.add_parser("project", help="list or add projects under 10_projects/")
    proj_sub = proj.add_subparsers(dest="project_command", required=True)
    p = proj_sub.add_parser("list", help="list project folder names")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.set_defaults(func=_cmd_project_list)
    p = proj_sub.add_parser("add", help="create a project skeleton")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--name", required=True, help="project slug under 10_projects/")
    p.set_defaults(func=_cmd_project_add)

    # claim
    claim = sub.add_parser("claim", help="session claim acquire / gate / status / close")
    claim_sub = claim.add_subparsers(dest="claim_command", required=True)

    p = claim_sub.add_parser("gate", help="pre-write conflict check (advisory, not a lock)")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--path", action="append", dest="paths", default=[])
    p.add_argument("--session-id", default=None)
    p.add_argument("--claim", default=None)
    p.add_argument("--ignore-invalid-claims", action="store_true")
    p.add_argument("--fail-on-expired", action="store_true")
    p.set_defaults(func=_cmd_claim_gate)

    p = claim_sub.add_parser("status", help="validate all session claims")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--fail-on-expired", action="store_true")
    p.set_defaults(func=_cmd_claim_status)

    p = claim_sub.add_parser("acquire", help="create a narrow claim file")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--session-id", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--path", action="append", dest="paths", default=[], required=True)
    p.add_argument("--claimed-by", default="agent-brain-cli")
    p.add_argument("--hours", type=int, default=8, help="claim TTL hours (default 8)")
    p.add_argument("--filename", default=None, help="optional filename under session_claims/")
    p.set_defaults(func=_cmd_claim_acquire)

    p = claim_sub.add_parser("close", help="mark a claim closed (local file edit)")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--claim", required=True, help="vault-relative claim path")
    p.add_argument("--summary", default="Closed via agent-brain claim close")
    p.set_defaults(func=_cmd_claim_close)

    # record
    rec = sub.add_parser("record", help="record helpers (validate, id)")
    rec_sub = rec.add_subparsers(dest="record_command", required=True)
    p = rec_sub.add_parser("validate", help="run memory governance checks")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--strict-soft", action="store_true")
    p.add_argument("--no-soft", action="store_true")
    p.set_defaults(func=_cmd_record_validate)
    p = rec_sub.add_parser("id", help="generate a stable record_id (ULID)")
    p.add_argument("--prefix", default="mem")
    p.set_defaults(func=_cmd_record_id)

    # retrieve (derived FTS — not truth)
    ret = sub.add_parser(
        "retrieve",
        help="derived SQLite FTS5 retrieval (candidates only; reopen Markdown)",
    )
    ret_sub = ret.add_subparsers(dest="retrieve_command", required=True)
    p = ret_sub.add_parser("rebuild", help="rebuild index under 50_retrieval/indexes/")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.set_defaults(func=_cmd_retrieve_rebuild)
    p = ret_sub.add_parser("search", help="search index with hard filters + FTS")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("query", help="free-text query")
    p.add_argument("--project", default=None)
    p.add_argument("--record-type", default=None)
    p.add_argument("--state", default=None)
    p.add_argument("--freshness", default=None)
    p.add_argument("--scope", default=None)
    p.add_argument("--risk-boundary", default=None)
    p.add_argument("--include-inactive", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_retrieve_search)

    # context builder
    ctx = sub.add_parser("context", help="build minimal sufficient project context pack")
    ctx_sub = ctx.add_subparsers(dest="context_command", required=True)
    p = ctx_sub.add_parser("build", help="pack overview/work/decisions/validation/handoff + FTS")
    p.add_argument("vault", nargs="?", type=Path, default=Path("."))
    p.add_argument("--project", required=True)
    p.add_argument("--task", default="", help="task string used for FTS candidates")
    p.add_argument("--max-tokens", type=int, default=16000)
    p.add_argument("--fts-limit", type=int, default=5)
    p.add_argument("--no-rebuild", action="store_true", help="do not auto-rebuild missing index")
    p.add_argument("--json", action="store_true", help="emit JSON instead of markdown pack")
    p.add_argument("--meta-only", action="store_true", help="with --json, omit document body")
    p.add_argument("--write", type=Path, default=None, help="also write markdown pack to path")
    p.set_defaults(func=_cmd_context_build)

    # deferred deeper memory promotion
    p = sub.add_parser("memory", help="planned for 0.8.0 (promotion / supersede workflows)")
    p.set_defaults(func=lambda args: _cmd_deferred("memory", "0.8.0"))

    # meta
    p = sub.add_parser("version", help="print version")
    p.set_defaults(func=lambda args: (print(__version__), 0)[1])

    p = sub.add_parser("repo-root", help="print detected repository root (debug)")
    p.set_defaults(func=lambda args: (print(repo_root()), 0)[1])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
