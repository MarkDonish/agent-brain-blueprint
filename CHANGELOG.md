# Changelog

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
