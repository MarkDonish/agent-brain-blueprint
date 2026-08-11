# Optimization Notes (0.3.0)

Date: 2026-08-11

## Decisions

1. **Schemas are JSON, not YAML**
   - Reason: keep zero third-party dependencies and avoid a fragile custom YAML parser.
   - Location: `schemas/*.json`
   - Scripts still accept the conceptual model described in the optimization brief.

2. **Frontmatter parser is a strict subset**
   - Supports scalars, quoted strings, booleans, numbers, null, and indented lists.
   - Duplicate keys and malformed lines become line-numbered errors.

3. **`dry_run_status` enum stays broad**
   - Accepts both short forms (`pass`/`fail`) and longer forms (`passed`/`failed`/`not_run`/`blocked`) for compatibility with existing local vaults.

4. **`expires_at` and `claimed_by` start optional**
   - Expired active claims become warnings (non-failing) unless `--fail-on-expired` / doctor `--strict`.
   - This hardens concurrency without breaking older claim files.

5. **Governance expansion is graded**
   - Strict: global + project decisions.
   - Soft: validation, handoffs, session claims (warnings unless `--strict-soft`).

6. **Claim gate is advisory, not a lock**
   - `check_claim_gate.py` only reports conflicts for planned paths.

## Non-goals retained

- No distributed lock service
- No vector DB / embedding runtime
- No secret storage in vault examples

## Release workflow (local-first)

1. Optimize and dogfood locally first.
2. Extract only reusable technical content for the public repo.
3. Never publish personal logs, private paths, secrets, customer data, or raw conversations.
4. Run `make verify` and `python3 scripts/check_privacy_scan.py .` before push.

