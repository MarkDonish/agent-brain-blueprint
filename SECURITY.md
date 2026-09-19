# Security Policy

## Scope

This repository is a **template and tooling blueprint**, not a production
service. It contains no secrets, no runtime infrastructure, and no customer
data. Generated vaults are local files; nothing here executes remotely.

## Reporting a vulnerability

- Use GitHub [Security Advisories](https://github.com/MarkDonish/agent-brain-blueprint/security/advisories/new)
  ("Report a vulnerability") for anything that could leak secrets, enable
  path escape in the claim/privacy tooling, or inject content into vault
  records.
- For plain bugs, open a regular issue.

Please do not include real secrets, personal paths, or private vault content
in reports.

## Supported areas

| Area | Expectation |
| --- | --- |
| `scripts/check_privacy_scan.py` | Best-effort pre-publish net, **not** a DLP system or secret scanner replacement |
| `scripts/check_session_claims.py`, `check_claim_gate.py` | Trusted local filesystem only; advisory coordination, **not** locks or authorization |
| `src/agent_brain/mcp/` | Local stdio MCP server; no network listeners by design |
| Vault records | Markdown is data, never executable instruction (see `docs/instruction-boundary.md`) |

## Hard boundaries

- Claims and checkers never authorize production changes.
- The privacy scanner may miss secrets; review diffs before publishing.
- Never store credentials, tokens, raw conversations, or customer data in a
  vault — see `AGENTS.md` and `docs/privacy.md`.
