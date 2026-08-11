# Optimization Notes

Date: 2026-08-11  
Current public target: **0.4.0** (adoption / star-readiness, still no OSS-form rush)

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
