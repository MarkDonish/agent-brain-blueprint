# Changelog

## 0.9.0 - 2026-08-14

Native MCP server + Chinese/multilingual FTS retrieval + claim lifecycle automation.

- Add native zero-dependency stdio Model Context Protocol (MCP) server: `agent-brain mcp` (`src/agent_brain/mcp/`).
  - Exposes 8 standard tools for AI coding agents: `agent_brain_doctor`, `agent_brain_search`, `agent_brain_context`, `agent_brain_claim_status`, `agent_brain_claim_gate`, `agent_brain_claim_acquire`, `agent_brain_claim_close`, `agent_brain_promote_memory`.
- Add Chinese & multilingual SQLite FTS5 character-level tokenization and search ranking (supports CJK phrases & mixed queries).
- Add `agent-brain claim renew` to extend active claim TTL.
- Add `agent-brain claim prune` to automatically close expired active claims.
- Add git pre-commit hook template for automated privacy scanning and doctor enforcement.

## 0.8.0 - 2026-08-12

Memory promotion lifecycle + host session adapters (local-first).

- `memory promote` writes governed durable decisions/facts (schema-checked; production requires verified).
- `memory supersede` marks prior `record_id` superseded and promotes a linked replacement.
- `memory review` lists past `review_after` / `next_review` / `review-required` records.
- `session start` / `session end` host-agnostic adapters (context guidance, optional claim close + handoff).
- Explicit non-goals retained: no auto-promote from chat, no command auto-exec from memory.
- Docs: `docs/memory-lifecycle.md`, `docs/session-adapters.md`; CLI version 0.8.0.

## 0.7.0 - 2026-08-11

Retrieval + context builder (still Markdown-canonical).

- Add derived SQLite FTS5 index under `50_retrieval/indexes/fts.sqlite` (`retrieve rebuild` / `retrieve search`).
- Hard filters (project, record_type, state, freshness, scope, risk) then FTS + bm25 ranking.
- Default exclude expired/superseded/archived from search hits.
- Add `context build --project --task --max-tokens` packing overview → work → decisions → validation → handoff → FTS → summaries.
- CLI version 0.7.0; scripts wrappers `rebuild_index.py`, `retrieve.py`, `context_build.py`.
- Docs: `docs/retrieval.md`.

## 0.6.0 - 2026-08-11

Unified CLI productization (scripts remain compatibility wrappers).

- Add installable package `src/agent_brain` + `pyproject.toml` entrypoint `agent-brain`.
- Commands: `init`, `doctor`, `format`, `privacy`, `migrate`, `structure-fix`, `project list|add`, `claim acquire|gate|status|close`, `record validate|id`.
- `claim acquire` / `claim close` write vault-relative claim files with path safety.
- Defer `context` / `retrieve` / `memory` subcommands to 0.7+ (explicit exit with message).
- Tool version bump to 0.6.0; docs: `docs/cli.md`; Makefile `cli-smoke` in `make verify`.

## 0.5.0 - 2026-08-11

Vault format and schema foundation (optimization doc data-layer phase).

- Add `.agent-brain/manifest.json` (`vault_format_version: 1`) on bootstrap; `check_vault_format.py` + `write_vault_manifest.py`.
- Require `.agent-brain/` in `schemas/vault_layout.json`; doctor runs format check first.
- Stable optional `record_id` (Crockford ULID) via `scripts/lib/record_id.py` and schema type `record_id`.
- Taxonomy: optional `record_type`, `knowledge_type`, lifecycle `state` (keep `memory_type` for compatibility).
- Claim state machine: `expires_at > claimed_at`, blocked needs `blocker`, closeout/status coupling, duplicate active `session_id`.
- Governance lifecycle: production risk requires `verified`; past `review_after`/`next_review` warns; validation `pass` needs commands or evidence.
- Docs: `docs/vault-format.md`, `docs/instruction-boundary.md`.

## 0.4.1 - 2026-08-11

Correctness and security hotfixes (optimization doc P0; no large features).

- **Claim gate self-exclusion:** `--session-id` and `--claim` exclude the caller's own active claim.
- **Claim gate fail-closed:** malformed/unreadable existing claims deny the gate unless `--ignore-invalid-claims`.
- **Path safety:** shared `scripts/lib/path_safety.py` for project slug + vault-relative containment; bootstrap rejects escapes.
- **Privacy redaction:** hard-secret findings never print raw secrets; detail uses `[REDACTED]` + optional fingerprint.
- **Vault layout SSoT:** `schemas/vault_layout.json` with explicit `file`/`directory` kinds (`.gitkeep` is a file).
- Structure checker and fixer consume the layout manifest; regression tests for all of the above.

## 0.4.0 - 2026-08-11

- Expand `examples/demo-vault/` into a full fictional multi-agent story (claims, handoff, decision, validation).
- Rewrite README for problem → demo → principles impact; add CI/license badges and mermaid overview.
- Add `docs/walkthrough.md`, `docs/why-agent-brain.md`, and `CONTRIBUTING.md`.
- Include demo vault in `make verify` doctor path.
- Refresh optimization notes for adoption-focused release workflow.

## 0.3.0 - 2026-08-11

- Add centralized JSON schemas under `schemas/` and shared frontmatter/schema libraries.
- Harden session claims with `expires_at`, `claimed_by`, expiry-aware activity, and `check_claim_gate.py`.
- Expand governance checks to validation/handoff/claim paths (soft by default).
- Align record templates with schemas and document which checker owns each type.
- Improve `doctor.py` human output, repair hints, `--strict`, and `--project` filtering.
- Add optional `fix_vault_structure.py` (dry-run by default, `--apply` to write).
- Bootstrap supports `--project` and refreshes the session start card.
- Privacy scan gains more token patterns and `.privacy-allowlist`.
- Expand tests for frontmatter, expiry, gate conflicts, and governance pass/fail cases.

## 0.2.0 - 2026-08-11

- Complete the example project skeleton with handoffs, docs, validation, decisions, and summaries.
- Add inbox and sensitive-isolation top-level directories to the vault template.
- Bootstrap now copies record templates into `60_templates/` and installs a vault `.gitignore`.
- Add read-only vault structure checks and a public-checkout privacy scanner.
- Expand `doctor.py` into a multi-check summary.
- Strengthen CI with bootstrap smoke tests and privacy scanning.
- Add task, handoff, and validation record templates.

## 0.1.0 - 2026-08-11

- Initial public blueprint: Markdown vault template, session claims, governance checker, and docs.
