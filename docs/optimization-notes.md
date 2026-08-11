# Optimization Notes

Date: 2026-08-11  
Current public target: **0.6.0** (unified CLI)

## 0.6.0 shipped (CLI)

1. `python -m agent_brain` / `agent-brain` entrypoint (`src/agent_brain`).
2. Init/doctor/privacy/migrate/project/claim/record commands wrap existing scripts.
3. Claim acquire/close as first-class local file operations (still not a lock).
4. Zero third-party runtime deps; scripts kept for compatibility.

## 0.5.0 shipped (format foundation)

1. Vault manifest + format checker + layout includes `.agent-brain/`.
2. Optional stable `record_id` (ULID).
3. Optional `record_type` / `knowledge_type` / lifecycle `state`.
4. Claim state-machine invariants + duplicate session_id detection.
5. Governance lifecycle soft rules + validation evidence soft rule.
6. Instruction-boundary and vault-format docs.

## 0.4.1 shipped (P0)

1. Claim gate excludes own `session_id` (`--session-id` / `--claim`).
2. Claim gate fails closed on invalid existing claims.
3. Shared path safety for project slugs and vault-relative paths.
4. Privacy scanner redacts hard secrets in reports (CI-safe).
5. `schemas/vault_layout.json` is SSoT for skeleton file/dir kinds.

## Decisions

1. **Schemas are JSON, not YAML**
   - Reason: keep zero third-party dependencies and avoid a fragile custom YAML parser.
   - Location: `schemas/*.json`

2. **Frontmatter parser is a strict subset**
   - Supports scalars, quoted strings, booleans, numbers, null, and indented lists.
   - Duplicate keys and malformed lines become line-numbered errors.

3. **`dry_run_status` enum stays broad**
   - Accepts both short forms (`pass`/`fail`) and longer forms (`passed`/`failed`/`not_run`/`blocked`).

4. **`expires_at` and `claimed_by` start optional**
   - Expired active claims become warnings unless `--fail-on-expired` / doctor `--strict`.

5. **Governance expansion is graded**
   - Strict: global + project decisions.
   - Soft: validation, handoffs, session claims (warnings unless `--strict-soft`).

6. **Claim gate is advisory, not a lock**
   - `check_claim_gate.py` only reports conflicts for planned paths.

7. **Demo vault is fictional and complete**
   - `examples/demo-vault` is a real skeleton with two non-overlapping claims so
     newcomers can run doctor/claim-gate without bootstrapping first.
   - Demo claim `expires_at` is far-future so the concurrent story stays runnable.

8. **Adoption before application**
   - Optimize README, demo, contribution path, and GitHub metadata first.
   - Wait for stars / real usage signals before Codex for OSS application.

## Non-goals retained

- No distributed lock service
- No vector DB / embedding runtime
- No secret storage in vault examples
- No private Agent-Brain dump into the public repo

## Release workflow (local-first)

1. Optimize and dogfood locally first.
2. Extract only reusable technical content for the public repo.
3. Never publish personal logs, private paths, secrets, customer data, or raw conversations.
4. Run `make verify` and `python3 scripts/check_privacy_scan.py .` before push.

## Star / adoption backlog (next)

- Social preview / banner asset (optional)
- Issue templates for “does not fit my host”
- Short terminal GIF of doctor + claim gate (optional, no private paths)
- Topics + description keep aligned with multi-agent + Codex keywords
