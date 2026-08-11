# Agent Brain Blueprint

A local-first, Markdown-native operating model for shared AI-agent memory.

This repository is a reusable blueprint, not a personal memory dump. It gives
Codex, Claude Code, and other agents a small, auditable place to share project
state, handoffs, durable decisions, validation records, and retrieval hints.

## What it solves

- A new agent can find the relevant project context without loading every past conversation.
- Markdown is the canonical record; indexes and search systems only nominate candidates.
- Personal memory, runtime configuration, secrets, logs, and databases stay outside the vault.
- Concurrent sessions can declare a narrow file claim before work and use a read-only closeout check.
- Durable facts carry provenance, confidence, freshness, scope, ownership, and risk boundaries.

## Design principles

1. **Markdown first.** Everything important remains readable, diffable, and portable.
2. **Retrieval is not truth.** Reopen the source Markdown or the real runtime before acting.
3. **Project before chat.** Organize by project state, handoff, validation, decision, and source material.
4. **Minimal context.** Read an entry card, then retrieve only what the task needs.
5. **No silent writes.** Claims, closeout, and promotion of durable facts are explicit.
6. **Privacy by construction.** Never put credentials, raw conversations, customer data, databases, or logs in the vault.

## Quick start

```bash
git clone https://github.com/MarkDonish/agent-brain-blueprint.git
cd agent-brain-blueprint
python3 scripts/bootstrap.py --destination ../my-agent-brain --project example-app
python3 scripts/doctor.py ../my-agent-brain
python3 scripts/check_claim_gate.py ../my-agent-brain \
  --path 10_projects/example-app/10_current_work/INDEX.md
python3 scripts/check_privacy_scan.py .
```

Bootstrap creates a new local vault from the templates, copies record templates
into `60_templates/`, installs a vault `.gitignore`, and refuses non-empty
destinations.

## Repository layout

```text
AGENTS.md                         shared operating rules for agent hosts
docs/                             architecture, privacy, claims, optimization notes
schemas/                          JSON field contracts (single source of truth)
templates/vault/                  bootstrap source
templates/*.md                    record templates aligned to schemas
scripts/                          dependency-free validation tools
scripts/lib/                      shared frontmatter + schema helpers
tests/                            regression tests
examples/demo-vault/              fictional, safe reference note
```

## Session claims and closeout

Before changing shared memory, create a session claim from
`templates/session_claim.md`. Recommended fields now include:

- `claimed_by` — which agent/host owns the claim
- `expires_at` — when the claim stops being treated as active

```bash
python3 scripts/check_session_claims.py ./my-agent-brain
python3 scripts/check_claim_gate.py ./my-agent-brain \
  --path 10_projects/example-app/10_current_work/INDEX.md
```

Important limits:

- claim checks are read-only and local-filesystem only
- dry-run fields are self-attested metadata
- this is **not** a distributed lock

See [session claims and closeout](docs/session-claims-and-closeout.md).

## Tooling

| Script | Purpose |
| --- | --- |
| `scripts/bootstrap.py` | Create a new local vault (`--project` supported) |
| `scripts/doctor.py` | Structure + governance + claims with repair hints |
| `scripts/check_vault_structure.py` | Skeleton existence |
| `scripts/check_memory_governance.py` | Strict decisions + soft validation/handoff/claims |
| `scripts/check_session_claims.py` | Claim shape, expiry, path conflicts |
| `scripts/check_claim_gate.py` | Pre-write conflict check for planned paths |
| `scripts/check_privacy_scan.py` | Pre-publish secret/path scan |
| `scripts/fix_vault_structure.py` | Optional dry-run/`--apply` skeleton repair |

Field contracts live in `schemas/*.json`.

## Privacy boundary

Do not add credentials, private chats, customer data, databases, logs, or
absolute private paths to the public repository or generated vault examples.

```bash
python3 scripts/check_privacy_scan.py .
python3 scripts/check_privacy_scan.py . --strict
```

Optional allowlist file: `.privacy-allowlist`.

## Verification

```bash
make verify
```

## License

MIT. See [LICENSE](LICENSE).
